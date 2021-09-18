use async_trait::async_trait;
use serenity::client::{Client, Context, EventHandler};
use serenity::framework::standard::buckets::LimitedFor;
use serenity::framework::standard::Args;
use serenity::framework::standard::{
    macros::{command, group, hook},
    CommandResult, StandardFramework,
};
use serenity::model::channel::Message;
use serenity::model::prelude::*;
use songbird::input::Restartable;
use songbird::SerenityInit;

use std::env;

#[group]
#[commands(play, repeat_for, repeat_off, setvol, pause, resume, leave)]
#[summary = "Commands for playing music with friends!"]
struct Audio;

struct Handler;

#[async_trait]
impl EventHandler for Handler {
    async fn ready(&self, ctx: Context, r: Ready) {
        ctx.set_presence(
            Some(Activity::playing("listening to music!")),
            OnlineStatus::Online,
        )
        .await;

        println!("Logged on with {}#{}", r.user.name, r.user.discriminator);
    }
}

#[tokio::main]
async fn main() {
    let framework = StandardFramework::new()
        .configure(|c| c.prefix("-").delimiters(vec![", ", " "]))
        .before(before)
        .bucket("complicated", |b| {
            b.limit(1)
                .time_span(10)
                .delay(5)
                .limit_for(LimitedFor::Channel)
                .await_ratelimits(1)
                .delay_action(delay_action)
        })
        .await
        .group(&AUDIO_GROUP);

    // Login with a bot token from the environment
    let token = env::var("DISCORD_TOKEN").expect("token");
    let mut client = Client::builder(token)
        .event_handler(Handler)
        .framework(framework)
        .register_songbird()
        .await
        .expect("Error creating client");

    // start listening for events by starting a single shard
    if let Err(why) = client.start().await {
        println!("An error occurred while running the client: {:?}", why);
    }
}

#[hook]
async fn before(_ctx: &Context, msg: &Message, command_name: &str) -> bool {
    println!(
        "Got command '{}' by user '{}'",
        command_name, msg.author.id
    );
    true
}

#[hook]
async fn delay_action(ctx: &Context, msg: &Message) {
    // You may want to handle a Discord rate limit if this fails.
    let _ = msg.react(ctx, '⏱').await;
}

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
