use serenity::{
    client::Context,
    framework::standard::{
        macros::{command, group},
        Args, CommandResult,
    },
    model::{channel::Message, prelude::*},
};
use songbird::input::Restartable;

#[group]
#[commands(play, repeat_for, repeat_off, setvol, pause, resume, leave, queue)]
#[summary = "Commands for playing music with friends!"]
struct Audio;

/// Retrieve the guild and channel ID of the user who invoked the given command.
async fn user_voice_state(
    ctx: &Context,
    msg: &Message,
) -> Result<(GuildId, ChannelId), &'static str> {
    match msg
        .guild(ctx)
        .await
        .unwrap()
        .voice_states
        .get(&msg.author.id)
    {
        Some(&VoiceState {
            guild_id: Some(guild_id),
            channel_id: Some(channel_id),
            ..
        }) => Ok((guild_id, channel_id)),
        _ => Err("fail"),
    }
}

#[command]
/// Play some audio source or add it to the queue.
async fn play(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    msg.reply(ctx, "Joining your channel now!").await?;
    let (guild_id, channel_id) = match user_voice_state(ctx, msg).await {
        Ok(s) => s,
        Err(_) => {
            msg.reply(
                ctx,
                format!("I couldn't find the channel you're in! Try leaving then joining again!"),
            )
            .await?;
            return Ok(());
        }
    };

    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");

    if let None = bird.get(guild_id) {
        match bird.join(guild_id, channel_id).await {
            (call_lock, Ok(())) => {
                let mut call = call_lock.lock().await;

                for uri in args.iter::<String>() {
                    call.enqueue_source(
                        Restartable::ytdl(uri.unwrap(), true)
                            .await
                            .expect("failed to queue")
                            .into(),
                    );
                }
            }
            _ => {}
        }
    }
    Ok(())
}

#[command]
#[aliases(loop)]
/// Loop the currently playing source for some set number of times, or
/// indefinitely.
async fn repeat_for(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let times = match args.single::<usize>() {
        Ok(u) => Some(u),
        Err(_) => None,
    };
    if !args.is_empty() {
        msg.reply(ctx, "Improper number of arguments.").await?;
        return Ok(());
    } else {
        msg.reply(ctx, "Looping your track.").await?;
    }

    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");

    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        match (times, call.queue().current()) {
            (_, None) => {
                msg.reply(ctx, "Nothing is playing!").await;
            }
            (None, Some(track)) => {
                track.enable_loop();
            }
            (Some(u), Some(track)) => {
                track.loop_for(u);
            }
        }
    }

    Ok(())
}

#[command]
#[aliases(stoploop, noloop)]
async fn repeat_off(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");

    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        match call.queue().current() {
            Some(track) => {
                track.disable_loop();
            }
            None => {
                msg.reply(ctx, "Nothing is playing!").await;
            }
        }
    }

    Ok(())
}

#[command]
/// Set the volume of the current streaming source.
async fn setvol(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let volume = args.single().unwrap();

    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        call.queue()
            .current()
            .expect("nothing playing")
            .set_volume(volume);
    }
    Ok(())
}

#[command]
/// Pause the current stream.
async fn pause(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        call.queue().current().expect("nothing playing").pause();
    }
    Ok(())
}

#[command]
/// Resume the current stream.
async fn resume(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        call.queue().current().expect("nothing playing").play();
    }
    Ok(())
}

#[command]
async fn leave(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    bird.leave(msg.guild_id.expect("need guild ID")).await;
    Ok(())
}

#[command]
async fn queue(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        if let Err(e) = msg
            .reply(
                ctx,
                call.queue()
                    .current_queue()
                    .iter()
                    .fold(String::new(), |acc, t| {
                        let metadata = t.metadata();
                        format!("{} {:?} {:?}", acc, metadata.artist, metadata.title)
                    }),
            )
            .await
        {
            eprintln!("Failed to reply: {}", e);
        }
    }
    Ok(())
}
