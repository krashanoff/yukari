use serenity::{
    client::Context,
    framework::standard::{
        macros::{command, group},
        Args, CommandResult,
    },
    model::channel::Message,
};

#[group]
#[commands(one_time_invite, rm)]
#[summary = "Shortcuts for common actions"]
struct Utility;

#[command]
#[aliases(oti)]
#[owners_only]
async fn one_time_invite(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let timeout = args.single().unwrap();
    let invite = ctx
        .cache
        .guild_channel(msg.channel_id)
        .await
        .unwrap()
        .create_invite(ctx, |i| i.max_uses(1).max_age(timeout))
        .await
        .expect("Failed to create an invite");
    msg.reply(ctx, format!("{}", invite.code))
        .await
        .expect("failed to send message");
    Ok(())
}

#[command]
#[aliases(rmoti)]
#[owners_only]
async fn rm(ctx: &Context, msg: &Message, mut args: Args) -> CommandResult {
    let code = args.single::<String>().unwrap();
    let invites = msg.guild(ctx).await.unwrap().invites(ctx).await.unwrap();
    for invite in invites {
        if invite.code == code {
            invite.delete(ctx).await;
        }
    }
    Ok(())
}
