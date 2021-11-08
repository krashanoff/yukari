use async_trait::async_trait;
use clap::{App, Arg};
use serde::{Deserialize, Serialize};
use serenity::{
    client::{Client, Context, EventHandler},
    framework::standard::{buckets::LimitedFor, macros::hook, StandardFramework},
    model::{channel::Message, prelude::*},
};
use songbird::SerenityInit;

use std::{fs::OpenOptions, path::PathBuf};

// We keep our command archetypes organized by module.
mod audio;
mod util;

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Config {
    token: String,
    owner: String,
    credentials: Option<PathBuf>,
    spreadsheet: Option<String>,
}

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
    let matches = App::new("yukari")
        .arg(
            Arg::with_name("config")
                .short("c")
                .long("config")
                .value_name("PATH")
                .required(true)
                .help("Path to config file"),
        )
        .get_matches();

    let config: Config = serde_json::from_reader(
        OpenOptions::new()
            .read(true)
            .write(false)
            .create(false)
            .open(matches.value_of("config").expect("config path is required"))
            .expect("failed to open config"),
    )
    .expect("failed to deserialize config");

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
        .group(&audio::AUDIO_GROUP)
        .group(&util::UTILITY_GROUP);

    // Login with a bot token from the environment
    let mut client = Client::builder(config.token)
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
    println!("Got command '{}' by user '{}'", command_name, msg.author.id);
    true
}

#[hook]
async fn delay_action(ctx: &Context, msg: &Message) {
    // You may want to handle a Discord rate limit if this fails.
    let _ = msg.react(ctx, '⏱').await;
}
