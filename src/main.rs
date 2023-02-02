use async_trait::async_trait;
use serde::{Deserialize, Serialize};
use serenity::{
    client::{Client, Context, EventHandler},
    framework::standard::{
        buckets::LimitedFor,
        help_commands,
        macros::{help, hook},
        Args, CommandGroup, CommandResult, HelpOptions, StandardFramework,
    },
    model::{channel::Message, prelude::*},
};
use songbird::SerenityInit;

use std::{collections::HashSet, fs::OpenOptions, path::PathBuf};

// We keep our command archetypes organized by module.
mod audio;
mod util;

const STATUSES: &[&'static str] = &[
    "listening to music!",
    "LEGO Ninjago with dad",
    "with fire",
    "best car alarm compilation 2012",
];

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
            Some(Activity::playing(
                STATUSES[rand::random::<usize>() % STATUSES.len()],
            )),
            OnlineStatus::Online,
        )
        .await;

        println!("Logged on with {}#{}", r.user.name, r.user.discriminator);
    }
}

#[tokio::main]
async fn main() {
    let config: Config = serde_json::from_reader(
        OpenOptions::new()
            .read(true)
            .write(false)
            .create(false)
            .open("config.json")
            .expect("failed to open config"),
    )
    .expect("failed to deserialize config");

    let framework = StandardFramework::new()
        .configure(|c| {
            c.prefix("~").delimiters(vec![", ", " "]).owners(
                vec![UserId(config.owner.parse::<u64>().expect("u64"))]
                    .into_iter()
                    .collect(),
            )
        })
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
        .help(&HELP)
        .group(&audio::AUDIO_GROUP)
        .group(&util::UTILITY_GROUP);

    // Login with a bot token from the environment
    let mut client = Client::builder(config.token, GatewayIntents::all())
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
        "Command '{}' issued by user '{}'",
        command_name, msg.author.id
    );
    true
}

#[hook]
async fn delay_action(ctx: &Context, msg: &Message) {
    // You may want to handle a Discord rate limit if this fails.
    let _ = msg.react(ctx, '⏱').await;
    let _ = msg.reply(ctx, "Hang tight! I'm on command cooldown.").await;
}

#[help]
async fn help(
    context: &Context,
    msg: &Message,
    args: Args,
    help_options: &'static HelpOptions,
    groups: &[&'static CommandGroup],
    owners: HashSet<UserId>,
) -> CommandResult {
    let _ = help_commands::with_embeds(context, msg, args, &help_options, groups, owners).await?;
    Ok(())
}
