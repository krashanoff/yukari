require("dotenv").config();
const Discord = require("discord.js");
const client = new Discord.Client();

const CMD_PREFIX = "~";

const Command = (name, description, usage, args, perms, call) => {
  this.name = name;
  this.description = description;
  this.usage = usage;
  this.args = args;
  this.perms = perms;
  this.call = call;
};

const CommandReturn = (stdout, donsole) => {
  this.stdout = stdout;
  this.donsole = donsole;
};

/**
 *
 * @param {Discord.Message} m The invocation message.
 * @param {string} c The contents to evaluate.
 *
 * @returns {CommandReturn} The result of evaluation.
 */
const evalCmd = (m, c) => {
  const ctx = {
    guilds: client.guilds,
    message: m,
    guild: m.guild,
  };
  let stdout = "";
  const donsole = {
    log: m => (stdout += `${m}\n`),
  };
  eval(c);
  console.log("Evaled");
  return { stdout };
};

// TODO: register commands here.
const REGISTERED_CMDS = {
  eval: Command(
    "eval",
    "",
    "",
    [String],
    //   isAdmin,
    evalCmd
  ),
};

client.on("ready", () => {
  console.log(`Logged in as ${client.user.tag}`);
});

client.on("message", m => {
  console.log(m.author.tag, m.content, process.env.OWNER);
  const evalExpr = m.content.match(/~eval ```js\n(.*)\n```/m);
  console.log(evalExpr);
  if (m.author.tag === process.env.OWNER && evalExpr) {
    console.info("OK");
    const result = evalCmd(m, evalExpr[1]);

    console.info(result);
    m.channel.send(
      `Evaluated to:\n# donsole:\n\`\`\`\n${result.stdout}\n\`\`\``
    );
  }
});

client.login(process.env.TOKEN);
