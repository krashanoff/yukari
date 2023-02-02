use serenity::{
    client::Context,
    framework::standard::{
        macros::{command, group},
        Args, CommandResult,
    },
    model::{channel::Message, prelude::*},
    utils::ArgumentConvert,
};
use songbird::input::Restartable;

#[group]
#[commands(
    play, play_now, repeat_for, repeat_off, set_vol, pause, resume, leave, queue, skip
)]
#[summary = "Commands for playing music with friends!"]
#[only_in(guilds)]
struct Audio;

/// Retrieve the guild and channel ID of the user who invoked the given command.
async fn user_voice_state(
    ctx: &Context,
    msg: &Message,
) -> Result<(GuildId, ChannelId), &'static str> {
    match msg.guild(ctx).unwrap().voice_states.get(&msg.author.id) {
        Some(&VoiceState {
            guild_id: Some(guild_id),
            channel_id: Some(channel_id),
            ..
        }) => Ok((guild_id, channel_id)),
        _ => Err("fail"),
    }
}

/// Add a track to the queue. Joins the bot to your current voice channel if it
/// isn't already connected.
#[command]
async fn play(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let url = match args.single::<String>() {
        Ok(url) => url,
        Err(_) => {
            return Ok(());
        }
    };

    let guild = msg.guild(&ctx.cache).unwrap();
    let guild_id = guild.id;

    let channel_id = guild
        .voice_states
        .get(&msg.author.id)
        .and_then(|voice_state| voice_state.channel_id);

    let connect_to = match channel_id {
        Some(channel) => channel,
        None => {
            return Ok(());
        }
    };

    let manager = songbird::get(ctx)
        .await
        .expect("Songbird Voice client placed in at initialisation.")
        .clone();
    let _handler = manager.join(guild_id, connect_to).await;

    if let Some(handler_lock) = manager.get(guild_id) {
        let mut handler = handler_lock.lock().await;

        let source = match Restartable::ytdl(url, true).await {
            Ok(source) => source,
            Err(why) => {
                println!("Err starting source: {:?}", why);
                return Ok(());
            }
        };

        if handler.queue().is_empty() {
            msg.reply(ctx, format!("Playing as requested!")).await;
        } else {
            msg.reply(ctx, format!("Queued at position {}", handler.queue().len()))
                .await;
        }

        handler.enqueue_source(source.into());
    } else {
        println!("err acquiring lock");
    }

    Ok(())
}

/// Play a track **immediately**.
#[command]
async fn play_now(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let url = match args.single::<String>() {
        Ok(url) => url,
        Err(_) => {
            return Ok(());
        }
    };

    let guild = msg.guild(&ctx.cache).unwrap();
    let guild_id = guild.id;

    let channel_id = guild
        .voice_states
        .get(&msg.author.id)
        .and_then(|voice_state| voice_state.channel_id);

    let connect_to = match channel_id {
        Some(channel) => channel,
        None => {
            return Ok(());
        }
    };

    let manager = songbird::get(ctx)
        .await
        .expect("Songbird Voice client placed in at initialisation.")
        .clone();
    let _handler = manager.join(guild_id, connect_to).await;

    if let Some(handler_lock) = manager.get(guild_id) {
        let mut handler = handler_lock.lock().await;

        handler.queue().stop();
        let source = match Restartable::ytdl(url, true).await {
            Ok(source) => source,
            Err(why) => {
                println!("Err starting source: {:?}", why);
                return Ok(());
            }
        };

        handler.enqueue_source(source.into());
    } else {
        println!("err acquiring lock");
    }

    play(ctx, msg, args).await
}

/// Loop the currently playing source for some set number of times, or
/// indefinitely.
#[command]
#[aliases(loop, repeatOne)]
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
                msg.reply(ctx, "Nothing is playing!")
                    .await
                    .expect("failed to send message");
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

/// Stop looping the current track.
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

/// Set the volume of the current streaming source.
#[command]
#[aliases(setvol, vol)]
async fn set_vol(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let volume = args.single().unwrap();

    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        if let Some(current) = call.queue().current() {
            current.set_volume(volume).expect("failed to set volume");
        }
        msg.reply(ctx, format!(":sound: Set volume to {}", volume))
            .await;
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

/// Resume the current stream.
#[command]
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

/// Leaves the voice channel.
#[command]
async fn leave(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;
        call.queue().stop();
    }
    bird.leave(msg.guild_id.expect("need guild ID")).await;
    msg.react(
        ctx,
        Emoji::convert(ctx, None, None, ":wave:").await.unwrap(),
    )
    .await;
    Ok(())
}

/// Prints out the current song queue.
#[command]
async fn queue(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;

        if call.queue().is_empty() {
            msg.reply(ctx, "Your queue is currently empty!").await;
            return Ok(());
        }

        if let Err(e) = msg
            .reply(
                ctx,
                call.queue()
                    .current_queue()
                    .iter()
                    .fold(String::new(), |acc, t| {
                        let metadata = t.metadata();
                        format!(
                            "{} {:?} {:?}\n",
                            acc,
                            metadata
                                .artist
                                .clone()
                                .unwrap_or_else(|| "Unknown".to_string()),
                            metadata
                                .title
                                .clone()
                                .unwrap_or_else(|| "Unknown".to_string())
                        )
                    }),
            )
            .await
        {
            eprintln!("Failed to reply: {}", e);
        }
    }
    Ok(())
}

/// Skips the current track.
#[command]
async fn skip(ctx: &Context, msg: &Message) -> CommandResult {
    let bird = songbird::get(ctx)
        .await
        .expect("failed to get songbird client");
    if let Some(call_lock) = bird.get(msg.guild_id.expect("need guild ID")) {
        let call = call_lock.lock().await;

        if call.queue().is_empty() {
            msg.reply(ctx, "Your queue is currently empty!").await;
            return Ok(());
        }

        call.queue().dequeue(0).unwrap();
    }
    Ok(())
}
