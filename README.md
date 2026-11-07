# PantryPal Room

**A family kitchen chat where AI agents track the pantry, warn before food expires, suggest meals that use it up, and draft the weekly shopping list, which only a family member can approve.**

Built with [Switch](https://github.com/sandbox-quantum/switch) for the [Flip the Switch hackathon](https://www.wemakedevs.org/hackathons/switch), Track 2: Best Personal or Creative Workflow.

> Demo video: _add your YouTube link here_
> Screenshot: _add a screenshot of the #kitchen room here_

## The problem

Families buy things they already have, forget what's in the fridge, and throw food away. Nobody owns the shopping list, so it lives in five people's heads.

## What PantryPal does

Everyone in the family chats in one room, `#kitchen`, with two AI agents:

| Who | Role |
| --- | --- |
| Family members | Say what they bought and used, in plain words ("bought 2 L milk", "used 4 eggs"), or post a photo of the grocery bill |
| **Pantry Keeper** agent | Updates the stock, asks when a message is unclear, warns about food expiring soon, then hands off to the Chef |
| **Chef** agent | Suggests meals that use the expiring food first, runs a family vote on dinner, and drafts the weekly shopping list |
| List owner (a person) | The only one who can approve the shopping list |

Every Sunday the Keeper posts a waste report: what went off, what it cost, and whether waste is going down.

## How Switch is used

Switch is what turns this from a script into a family workflow:

- **One shared room.** Switch turns the `#kitchen` channel into a room. Family members and both agents read the same history, so the Chef knows what the Keeper found, and Mom sees what Dad logged.
- **Agents as teammates.** Both agents join the room with their own names, through Switch Console, using Claude Code. They run the Python tools in this repo and reply in chat.
- **Hand-off between agents.** The Keeper finds expiring food and hands it to `@pantry-chef` by name. The Chef picks it up in the same thread.
- **The whole family talks to it.** `!assign-agent @pantry-keeper` makes the Keeper the room's main agent, so Mom and Dad can just say "bought milk" without tagging anyone. Messages that tag the Chef go to the Chef.
- **Photos go straight to the agent.** Switch passes a photo posted in the room to the Keeper, which reads the grocery bill, asks about anything unclear and adds nothing until the person who posted it says yes.
- **A family vote in the room.** The Chef offers two meals and counts everyone's votes in chat; the winner is cooked, and "made the palak paneer" updates the stock for every ingredient.
- **People stay in charge.** The shopping list is final only when the list owner approves it in chat. The Chef's instructions say so, and `tools/shopping_list.py` refuses an approval from anyone but the list owner (see [Known limitations](#known-limitations)).
- **The whole setup is one file.** `room/pantrypal.template.yaml` defines both agents, their instructions and the room. Switch Console reads it and creates everything.

Without Switch there is no room, no hand-off and no approval step: the project would stop working.

## Architecture

```
            Switch room: #kitchen (Mattermost)
 ┌─────────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │ Family members  │──▶│ Pantry Keeper    │──▶│ Chef             │
 │ log buys + uses │   │ updates stock,   │   │ meals + shopping │
 │ owner approves  │◀──┼──────────────────┼───│ list, asks owner │
 └─────────────────┘   └────────┬─────────┘   └────────┬─────────┘
                                │ runs                 │ runs
                     pantry.py, expiring.py   meals.py, shopping_list.py,
                                              weekly_report.py
                                │                      │
                                └──── data/*.json ─────┘
```

## Setup (about 15 minutes)

You need a Mac, [Docker Desktop](https://www.docker.com/products/docker-desktop/), Python 3.11+, Git, [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) and [Switch Console](https://github.com/sandbox-quantum/switch). The tools use only the Python standard library: there is nothing to `pip install`.

1. **Clone the repo**
   ```bash
   git clone https://github.com/<your-username>/pantrypal-room.git
   cd pantrypal-room
   ```
2. **Start Switch.** Follow the [Switch quickstart](https://docs.switchagents.ai/switch-rooms/getting-started). Switch Console runs Switch in Docker and comes with Mattermost.
3. **Create the people.** In Mattermost, create users for the family alongside your own account. With the Mattermost that Switch Console starts:
   ```bash
   MM="docker exec switchdash-local-mattermost-mattermost-1 mmctl --local"
   $MM user create --username mom --email mom@localhost.local --password 'choose-a-password'
   $MM user create --username dad --email dad@localhost.local --password 'choose-a-password'
   $MM team users add switch mom dad
   ```
4. **Reset the demo data**, with your own Mattermost username as list owner:
   ```bash
   python3 scripts/seed.py --owner <your-username>
   ```
5. **Load the room.** In Switch Console, load `room/pantrypal.template.yaml`. In the form, replace `{directory}` in **PantryPal repo folder** with the full path of your clone (run `pwd` in it to see it). Provider defaults to Claude Code and the messaging app to Mattermost; change them under Advanced if needed. Select **Create all**.
6. **Add the family to the room**, since the template adds only you:
   ```bash
   $MM channel users add switch:kitchen mom dad
   ```
7. **Check it works.** Both agents say hello in `#kitchen`.

## Run the demo

First, once per room, type `!assign-agent @pantry-keeper` in `#kitchen`. This makes the Keeper the room's main agent, so family members can just say "bought…" or "used…" without tagging it.

Then type these in `#kitchen`, one message per row. Log in as Mom and Dad in a private browser window. A message that tags an agent goes only to that agent, so keep the `@` names.

| Who | Message | What happens |
| --- | --- | --- |
| Mom | `bought 2 L milk ($2.58) and 12 eggs ($4.99)` | Keeper adds both items, with guessed expiry dates |
| Dad | `used 4 eggs for breakfast` | Keeper updates the stock |
| Dad | `used 30 eggs` | Keeper refuses: only 14 in stock, please check |
| You | `@pantry-keeper what's expiring?` | Spinach and paneer expire tomorrow; Keeper hands off to Chef |
| — | — | Chef suggests 1. palak paneer (uses both) and 2. banana milkshake, and asks the family to vote |
| Mom | `@pantry-chef 1` | Chef: "Votes so far: Palak paneer 1 (Mom), Banana milkshake 0" |
| Dad | `@pantry-chef 1` | Chef: Palak paneer 2 (Mom, Dad) |
| You | `@pantry-chef close the vote` | Chef: Palak paneer wins, "when it's cooked, tell the Keeper: @pantry-keeper made Palak paneer" |
| Mom | `@pantry-keeper made the palak paneer` | Keeper logs the whole recipe at once: 250 g spinach, 200 g paneer, 1 onion, 2 tomatoes |
| You | `@pantry-chef make this week's shopping list` | Chef drafts the list, skipping the milk Mom just bought, and asks you to approve |
| Dad | `@pantry-chef approved` | Chef waits: only the list owner can approve |
| You | `@pantry-chef remove potatoes, add 200 g paneer, approved` | Chef posts the final list |
| You | `@pantry-keeper weekly report` | 3 items wasted, about $3.06, down 67% from $9.20 last week |
| You | `@pantry-keeper got these today`, with [`demo/sample-bill.png`](demo/sample-bill.png) attached | Keeper reads the bill, lists 6 food items (1 L milk from 2 × 500 ml, carry bag left out) and asks how many tomatoes and onions, since it tracks those in pieces |
| You | `@pantry-keeper 8 tomatoes and 12 onions. yes` | Keeper adds all 6 items, $23.53 in total |

To run the demo again from the start: `python3 scripts/seed.py --owner <your-username>`.

## The tools

Each script prints JSON with a `message` the agents can post in chat.

| Command | What it does |
| --- | --- |
| `python3 tools/pantry.py add --item milk --qty 2 --unit L --expiry 2027-12-31 --price 56 --by Mom` | Record a purchase |
| `python3 tools/pantry.py use --item eggs --qty 4 --by Dad` | Record usage; uses the batch that expires first |
| `python3 tools/pantry.py cook --meal "palak paneer" --by Mom` | Record a meal cooked: uses every ingredient of the recipe, or changes nothing if one is short |
| `python3 tools/pantry.py discard --item spinach --by Mom` | Record food thrown away |
| `python3 tools/pantry.py list` | Show stock |
| `python3 tools/expiring.py --days 2` | Food expiring soon, and food already expired |
| `python3 tools/meals.py --days 2 --top 3` | Meals that use the soonest-expiring food first |
| `python3 tools/shopping_list.py draft` | Draft the list from staples running low |
| `python3 tools/shopping_list.py approve --by <owner> --remove onions --add "paneer:200:g"` | Approve the list (list owner only) |
| `python3 tools/weekly_report.py` | Waste this week vs last week, in $ |

Data lives in `data/`: `pantry.json` (stock, by purchase batch), `staples.json` (what the family always keeps), `recipes.json`, `history.json`, `settings.json` (list owner) and `approved_lists.json`.

## Tests

```bash
python3 -m unittest -v
```

The tests run every tool against a fresh copy of the demo data, with today's date fixed.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| **Create all** stays grey in Switch Console | **PantryPal repo folder** still says `{directory}` | Replace it with the full path of your clone |
| An agent doesn't reply | The message didn't tag it, or it's offline | Tag it (`@pantry-chef …`); type `!agents-status` to see who's live |
| "bought milk" gets no reply | No main agent in the room yet | Type `!assign-agent @pantry-keeper` once in `#kitchen` |
| The Chef ignores "approved" | The approval wasn't tagged, or it shared a message with another agent's tag | Send `@pantry-chef approved` as its own message |
| Mom or Dad can't post in `#kitchen` | The template adds only you to the room | `$MM channel users add switch:kitchen mom dad` (setup step 6) |

## Known limitations

- **The approval check trusts the name the Chef passes.** `shopping_list.py approve --by <name>` refuses anyone but the list owner, but the name comes from the Chef, which reads it from the chat. A Chef tricked into passing the owner's name would get past the check. A fix would read the sender from Switch itself instead of from the agent.
- **The agents can run commands on the computer they run on.** They are Claude Code sessions working in this repo, and the template lets anyone on your Switch server talk to them. Invite only people you trust, and keep **Bypass permissions** off in Switch Console so risky actions still ask first.
- **One unit per item.** Milk is tracked in litres, so "500 ml" must be converted first; the Keeper asks.
- **Bill photos are read by the agent, not by a parser.** A blurry or unusual bill can be misread, so the Keeper lists what it read and waits for a yes before adding anything.
- **Throwing food away empties every batch** of that item, including fresh ones.

## What's next

- A Python agent that joins the room through the Switch Agent Protocol and posts the expiry warning every morning on its own
- Moving the family chat to Telegram

## License

MIT. See [LICENSE](LICENSE).
