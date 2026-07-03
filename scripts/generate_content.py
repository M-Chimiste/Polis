#!/usr/bin/env python3
"""One-shot content generator for the POLIS v1 town.

Generation is a TOOLING step, not a sim dependency. This script emits static,
hand-editable JSON into content/. The sim only ever reads content/; it never
generates. Re-running this script REGENERATES FROM SCRATCH and will clobber
hand edits — after v1 content is ratified, edit the JSON directly and treat
this script as historical record.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

# ---------------------------------------------------------------- town ----
# 48x48 grid. Locations are axis-aligned rects with a door cell.
# privacy: 0 = fully public, 1 = fully private (perception/ social norms hook)

L = lambda id, name, kind, rect, door, privacy, tags=(): dict(
    id=id, name=name, kind=kind, rect=rect, door=door, privacy=privacy,
    tags=list(tags), objects=[])

town = {
    "id": "harrowmere",
    "name": "Harrowmere",
    "grid": {"width": 48, "height": 48},
    "description": (
        "A small inland village on a millstream. One square, one tavern, "
        "one chapel; everyone knows everyone, which is the point."
    ),
    "locations": [
        L("market_square",  "Market Square",        "public",    [18, 18, 12, 12], [24, 30], 0.0, ["gathering", "commerce"]),
        L("village_well",   "The Village Well",     "public",    [22, 14, 4, 4],   [24, 18], 0.0, ["gathering", "water"]),
        L("gilded_perch",   "The Gilded Perch",     "tavern",    [12, 30, 8, 6],   [16, 30], 0.1, ["gathering", "food", "drink", "lodging"]),
        L("crane_bakery",   "Crane Bakery",         "shop_home", [30, 30, 6, 5],   [32, 30], 0.3, ["food", "commerce"]),
        L("vosse_smithy",   "Vosse Smithy",         "shop_home", [10, 20, 6, 5],   [16, 22], 0.3, ["craft", "commerce"]),
        L("quill_store",    "Quill's General Goods","shop_home", [30, 20, 6, 5],   [30, 22], 0.2, ["commerce"]),
        L("marsh_cottage",  "Marsh Cottage",        "shop_home", [38, 12, 5, 5],   [38, 14], 0.5, ["herbalism", "healing"]),
        L("chapel",         "Chapel of the Lamp",   "chapel",    [20, 4, 8, 7],    [24, 11], 0.2, ["gathering", "teaching"]),
        L("ferrin_mill",    "Ferrin Mill",          "mill",      [4, 38, 7, 6],    [11, 40], 0.3, ["craft", "commerce", "millstream"]),
        L("hale_farm",      "Hale Farmstead",       "farm",      [36, 38, 10, 8],  [36, 42], 0.4, ["food", "fields"]),
        L("weaver_cottage", "Weaver Cottage",       "home",      [6, 8, 5, 5],     [11, 10], 0.6, []),
        L("tarn_cabin",     "Tarn Cabin",           "home",      [42, 4, 4, 4],    [42, 8],  0.8, ["edge_of_town"]),
        L("fenn_cottage",   "Fenn Cottage",         "home",      [14, 12, 5, 4],   [16, 16], 0.6, []),
        L("dunn_house",     "Dunn House",           "home",      [22, 38, 6, 5],   [22, 40], 0.5, ["reeve"]),
        L("ferrin_house",   "Ferrin House",         "home",      [4, 32, 5, 4],    [9, 34],  0.6, []),
        L("orchard",        "The Old Orchard",      "public",    [38, 24, 8, 8],   [38, 28], 0.2, ["food", "quiet"]),
    ],
    "occluders": [
        {"id": "market_stalls", "at": [23, 22], "radius": 1.5, "note": "stall row blocks sight across the square"},
        {"id": "chapel_yew",    "at": [19, 12], "radius": 1.2, "note": "old yew by the chapel door"},
    ],
    "notes": (
        "STATIC CONTENT. Generated once by scripts/generate_content.py and "
        "frozen; edit by hand from here on. Location ids are referenced by "
        "agent seeds and must not be renamed without running "
        "scripts/validate_content.py."
    ),
}

# --------------------------------------------------------------- agents ----
# Park-style seeds: paragraph bio, traits, anchors, initial memories.
# Relationships live in content/relationships.json (single edge list —
# one place to edit, validator enforces referential integrity).

def A(id, name, age, occupation, home, workplace, traits, bio, anchors, memories):
    return dict(
        id=id, name=name, age=age, occupation=occupation,
        home=home, workplace=workplace, traits=traits, bio=bio,
        daily_anchors=anchors, initial_memories=memories,
    )

def anchors(wake, work_start, midday, work_end, evening, sleep):
    return {"wake": wake, "work_start": work_start, "midday_meal": midday,
            "work_end": work_end, "evening_habit": evening, "sleep": sleep}

agents = [
A("maren_alder", "Maren Alder", 51, "tavernkeeper", "gilded_perch", "gilded_perch",
  ["shrewd", "warm", "unshockable"],
  "Maren has run the Gilded Perch for twenty-six years and has heard every secret in Harrowmere at least twice. She keeps them, mostly, which is why people keep bringing them. She measures the village's mood by what gets ordered.",
  anchors("06:00", "09:00", "13:00", "23:00", "tallying the ledger at the bar", "23:30"),
  ["The autumn ale is two barrels short of what the harvest crowd will drink.",
   "Piet has been quieter than usual this week."]),

A("piet_alder", "Piet Alder", 49, "brewer", "gilded_perch", "gilded_perch",
  ["methodical", "private", "dry-witted"],
  "Piet brews for the Perch and speaks roughly one sentence per barrel. He married into the tavern and never quite into its noise; his real conversations happen with the mash tuns in the back.",
  anchors("05:30", "06:00", "13:00", "18:00", "sitting at the quiet end of his own taproom", "22:00"),
  ["The new hops from the Hale fields are better than last year's.",
   "Ilse has been slipping off to Marsh Cottage again instead of working the floor."]),

A("ilse_alder", "Ilse Alder", 19, "tavern server", "gilded_perch", "gilded_perch",
  ["curious", "restless", "quick"],
  "Ilse grew up under the Perch's tables and knows the village's gossip circuits better than its lanes. Lately she spends every spare hour at Odile Marsh's cottage learning herb-lore, and hasn't yet told her parents she'd rather be a healer than a tavernkeeper.",
  anchors("07:00", "10:00", "13:30", "22:00", "reading borrowed herbals by candle", "23:00"),
  ["Odile said I have the memory for the work, which she does not say lightly.",
   "Mother expects me to take over the Perch someday. I haven't corrected her."]),

A("tobias_crane", "Tobias Crane", 38, "baker", "crane_bakery", "crane_bakery",
  ["exacting", "anxious", "generous"],
  "Tobias bakes before the village wakes and worries after it sleeps. His bread is the best for three villages, a fact he cannot enjoy because tomorrow's batch might not be. He gives the day-olds to whoever looks like they need them.",
  anchors("03:30", "04:00", "12:00", "14:00", "early to bed, listening to the oven cool", "20:30"),
  ["The mill's last flour sacks were coarser than Josta's usual grind.",
   "Sela handles the customers better than I ever will."]),

A("sela_crane", "Sela Crane", 36, "baker & stallkeeper", "crane_bakery", "market_square",
  ["gregarious", "sharp-tongued", "loyal"],
  "Sela runs the Crane market stall and the social front of the bakery. She trades bread for news at a favorable exchange rate and defends Tobias's moods to anyone who mistakes them for rudeness.",
  anchors("05:00", "08:00", "13:00", "16:00", "trading stories at the well", "21:30"),
  ["Petra Quill shorted the sugar order again — the second time this season.",
   "Josta will know why the flour's gone coarse before the miller's wife admits it."]),

A("garrick_vosse", "Garrick Vosse", 45, "blacksmith", "vosse_smithy", "vosse_smithy",
  ["stoic", "fair", "slow to anger, slower to forgive"],
  "Garrick's forge has shod every horse and mended every hinge in Harrowmere for two decades. He took Renn Odell in as apprentice after the boy's family scattered, and treats him with a gruffness indistinguishable, to Garrick, from affection.",
  anchors("06:00", "07:00", "12:30", "18:00", "one slow pint at the Perch", "22:00"),
  ["Renn's welds are nearly there. He doesn't believe it yet.",
   "The reeve still owes for the gate work from spring."]),

A("renn_odell", "Renn Odell", 17, "smith's apprentice", "vosse_smithy", "vosse_smithy",
  ["eager", "thin-skinned", "hardworking"],
  "Renn sleeps in the smithy loft and is trying to hammer himself into someone Harrowmere will keep. He watches Garrick for signs of approval the way farmers watch for rain, and spends what little he earns at Sela's stall because she talks to him like a grown man.",
  anchors("06:00", "07:00", "12:30", "18:30", "practicing scrollwork on scrap iron", "22:30"),
  ["Garrick let me handle the chapel lamp bracket alone. He didn't redo it after.",
   "Corin Hale is the only one my age who doesn't treat me like a stray."]),

A("odile_marsh", "Odile Marsh", 63, "herbalist", "marsh_cottage", "marsh_cottage",
  ["blunt", "observant", "unsentimental but kind"],
  "Widow Marsh has doctored Harrowmere's fevers, births, and bad decisions for thirty years. She says exactly what she thinks, charges exactly what people can pay, and has quietly decided Ilse Alder will be her successor whether the Alders like it or not.",
  anchors("06:30", "08:00", "13:00", "17:00", "tending the physic garden at dusk", "21:30"),
  ["Ilse learns in a week what took me a season. The girl is wasted on tankards.",
   "Old Nan's cough is back, and she'll hide it until it's serious."]),

A("bram_hale", "Bram Hale", 44, "farmer", "hale_farm", "hale_farm",
  ["steady", "proud", "stubborn about the land"],
  "Bram works the largest farmstead in Harrowmere the way his father did, which is both its strength and his blind spot. He's respected at the square and immovable at his own table, where Corin's daydreaming lands like a personal insult to three generations.",
  anchors("05:00", "05:30", "12:00", "19:00", "walking the fence line alone", "21:30"),
  ["The east field wants draining before the autumn rains or we lose the planting.",
   "Corin was staring at the clouds again when the fence wanted mending."]),

A("tessa_hale", "Tessa Hale", 42, "farmer", "hale_farm", "hale_farm",
  ["practical", "peacemaking", "quietly decisive"],
  "Tessa runs half the farm and all of its diplomacy. She translates between Bram's silences and Corin's wanderings, and most of the farmstead's actual decisions pass through her while appearing to be Bram's.",
  anchors("05:00", "06:00", "12:00", "18:30", "mending by the fire, listening", "21:30"),
  ["Bram and Corin haven't spoken past chores in a week. That has to break soon.",
   "Sela will trade preserves for bread through the winter if I ask before the frost."]),

A("corin_hale", "Corin Hale", 16, "farmhand", "hale_farm", "hale_farm",
  ["dreamy", "gentle", "quietly defiant"],
  "Corin does his chores adequately and his daydreaming superbly. He'd rather be at the mill listening to Dane's road stories or in the orchard doing nothing describable. He hasn't told his father that he doesn't want the farm; he suspects his mother already knows.",
  anchors("05:30", "06:00", "12:00", "18:00", "the orchard, or Renn at the smithy", "22:00"),
  ["Dane says the river towns take on carters' boys at sixteen.",
   "Father looked at me across the east field like he already knows."]),

A("josta_ferrin", "Josta Ferrin", 40, "miller", "ferrin_house", "ferrin_mill",
  ["talkative", "canny", "keeps score"],
  "Josta grinds Harrowmere's grain and processes its information with equal throughput. Nothing moves through the village without passing her millstream eventually, and she remembers who said what about whom for longer than is strictly healthy.",
  anchors("06:00", "07:00", "12:30", "17:30", "holding court at the well or the Perch", "22:00"),
  ["The millstone's dressing is overdue — that's why the grind's gone coarse, not that I've told the Cranes yet.",
   "Dane took the long road home from the river towns twice this month."]),

A("dane_ferrin", "Dane Ferrin", 41, "carter", "ferrin_house", "market_square",
  ["easygoing", "worldly", "avoids conflict"],
  "Dane hauls Harrowmere's goods to the river towns and returns with cargo, news, and a manner just a shade too relaxed for his wife's accounting. He's the village's window to elsewhere, and he likes being missed slightly more than being home.",
  anchors("06:30", "07:30", "13:00", "18:00", "a long pint and longer stories at the Perch", "22:30"),
  ["The river towns are paying half again over spring prices for good flour.",
   "Josta counts the days I'm gone. I should bring her something from the river."]),

A("anselm", "Brother Anselm", 58, "cleric & teacher", "chapel", "chapel",
  ["gentle", "bookish", "conflict-averse to a fault"],
  "Brother Anselm keeps the Chapel of the Lamp, teaches letters to whichever children can be spared from chores, and believes most village disputes would dissolve if people simply talked — a theory the village keeps disproving. He lends books he never gets back.",
  anchors("05:30", "08:00", "12:30", "17:00", "reading by the chapel lamp", "21:00"),
  ["Ilse returned the herbal, the only borrower who ever returns anything.",
   "The reeve and Garrick nodded past each other at the square again. That gate debt is festering."]),

A("petra_quill", "Petra Quill", 33, "shopkeeper", "quill_store", "quill_store",
  ["ambitious", "precise", "defensive"],
  "Petra inherited the general store young and runs it tightly, extending credit by a private ledger of who deserves it. She came back from two years in the river towns with ideas Harrowmere finds suspicious, and she finds Harrowmere's suspicion exhausting.",
  anchors("06:30", "07:30", "13:00", "18:30", "accounts, then a walk to the orchard", "22:00"),
  ["The sugar shipment was short from the supplier's end — Sela won't hear it.",
   "If Dane's right about river prices, a buying trip before winter would pay twice over."]),

A("nan_weaver", "Old Nan Weaver", 70, "weaver", "weaver_cottage", "weaver_cottage",
  ["storyteller", "sly", "frailer than she admits"],
  "Nan has woven cloth and narrative in Harrowmere longer than anyone's memory but her own. Children collect at her door for stories; adults collect there for the older, sharper ones. She hides her bad cough because being fussed over is worse than dying.",
  anchors("07:30", "09:00", "13:00", "16:00", "stories at her doorstep till the light goes", "21:00"),
  ["The cough is back. Odile will smell it on me within the week, the witch.",
   "Corin Hale sits at story-time with the little ones and thinks nobody notices."]),

A("luce_tarn", "Luce Tarn", 26, "hunter & trapper", "tarn_cabin", "tarn_cabin",
  ["solitary", "watchful", "dry"],
  "Luce keeps to the cabin at the wood's edge, trades game and pelts at the square, and answers questions in the fewest words the language allows. The village reads her solitude as strangeness; she reads their curiosity as noise. Odile is the only door she knocks on.",
  anchors("04:30", "05:00", "12:00", "16:00", "working hides, alone", "21:00"),
  ["Something's been taking rabbits from the north snares. Not a fox. Wrong prints.",
   "Odile asked for wolfsbane before the frost. I owe her for the winter fever."]),

A("mira_fenn", "Mira Fenn", 29, "seamstress", "fenn_cottage", "fenn_cottage",
  ["kind", "wistful", "harder underneath than she looks"],
  "Mira sews for the village and came back to her late mother's cottage after a marriage in the river towns ended in a way she doesn't discuss. Harrowmere half-remembers her as a girl and hasn't decided who she is now; neither, entirely, has she.",
  anchors("07:00", "08:30", "13:00", "18:00", "the well at dusk, then the Perch some nights", "22:00"),
  ["The reeve's mending is done three days early. No reason to deliver it early. No reason not to.",
   "Sela is the only one who asks nothing about the river towns."]),

A("cormac_dunn", "Cormac Dunn", 55, "reeve", "dunn_house", "market_square",
  ["dutiful", "vain about his fairness", "tired"],
  "Cormac has been Harrowmere's reeve for eleven years: settling boundary squabbles, keeping the square's peace, and absorbing blame with diminishing grace. He believes he is scrupulously fair and is almost right. The unpaid smithy debt embarrasses him too much to settle.",
  anchors("06:30", "08:00", "13:00", "17:30", "walking the square's perimeter, being seen", "22:00"),
  ["The Hale drainage will flood the mill path if Bram cuts it where he intends. Someone must tell him.",
   "I must settle with Garrick. After the harvest levy. Definitely after."]),

A("fenwick_roan", "Fenwick Roan", 22, "odd-jobber", "ferrin_mill", "market_square",
  ["cheerful", "unreliable", "surprisingly perceptive"],
  "Fenwick turned up two summers ago, sleeps in the mill loft in exchange for lifting sacks, and works for whoever pays by the day. Everyone agrees he's feckless; everyone hires him anyway. He notices far more than his grin lets on and hasn't decided what to do with any of it.",
  anchors("07:30", "09:00", "13:00", "17:00", "wherever the talk is — usually the Perch", "23:00"),
  ["Petra pays same-day and Bram pays eventually. Plan the week accordingly.",
   "Saw the reeve turn around rather than pass the smithy. Third time. Interesting."]),
]

# --------------------------------------------------------- relationships ----
# Single edge list: one place to edit. Undirected pair + per-direction view.
# closeness: 0..1 (interaction propensity prior). type is a loose label.

def E(a, b, type, closeness, a_view, b_view):
    return dict(a=a, b=b, type=type, closeness=closeness,
                a_view=a_view, b_view=b_view)

relationships = [
E("maren_alder","piet_alder","spouses",0.9,"He'd talk if the tavern were quieter. It never is.","She is the tavern. I just keep it in beer."),
E("maren_alder","ilse_alder","parent_child",0.85,"She'll run this place better than I do, once she settles.","She thinks I'm settling. I'm deciding."),
E("piet_alder","ilse_alder","parent_child",0.8,"She's at Marsh Cottage more than the taproom. I haven't told Maren.","Da knows. Da says nothing. That's Da."),
E("maren_alder","josta_ferrin","friends_rivals",0.6,"We trade the same gossip and pretend we don't.","Maren hears it first; I understand it first."),
E("garrick_vosse","renn_odell","master_apprentice",0.8,"The boy's good. Telling him would ruin the pace of it.","One day he'll say 'well done' and I'll probably drop the hammer."),
E("garrick_vosse","cormac_dunn","strained",0.4,"A reeve who preaches fairness and owes the smithy since spring.","Garrick's silence at the square is louder than any dun letter."),
E("tobias_crane","sela_crane","spouses",0.9,"She makes the bakery a place people like. I just make the bread.","He makes the bread. I make sure he eats."),
E("sela_crane","petra_quill","feud_commercial",0.5,"Twice-short on sugar is a habit, not a mishap.","Check my ledger against her memory any day."),
E("sela_crane","josta_ferrin","friends",0.7,"If Josta doesn't know it, it hasn't happened yet.","Sela's the only one who trades me news at fair rates."),
E("sela_crane","mira_fenn","friends",0.6,"She'll talk about the river towns when she's ready.","She never asks. Which is why I might someday tell her."),
E("tobias_crane","josta_ferrin","commercial_strained",0.5,"The flour's gone coarse and she knows why.","I'll dress the millstone before he works up the nerve to complain."),
E("bram_hale","tessa_hale","spouses",0.85,"Tessa keeps the peace. I keep the fields. Fair trade.","He thinks he decides things. I let him think it, mostly."),
E("bram_hale","corin_hale","parent_child_strained",0.6,"Three generations cleared that land. He stares at clouds.","He talks to the land more than to me. I stopped competing with dirt."),
E("tessa_hale","corin_hale","parent_child",0.85,"He's not made for the farm. Bram will hear it from me before winter.","Mum knows. Mum always knows first."),
E("corin_hale","renn_odell","friends",0.75,"Renn made something with his hands and it's still on the chapel wall. I want to feel that.","Corin doesn't care that I came from nowhere."),
E("corin_hale","dane_ferrin","mentor_informal",0.55,"Dane's seen past the second hill. Nobody else here has.","The boy listens like the road's a story. Reminds me of me, which should worry someone."),
E("corin_hale","nan_weaver","fond",0.5,"Her stories are the only maps of elsewhere I've got.","That boy is a leaving-shaped person. I've seen the shape before."),
E("josta_ferrin","dane_ferrin","spouses",0.75,"Twice this month, the long road home. I count because he doesn't.","She counts everything. It's how she loves. I think."),
E("josta_ferrin","fenwick_roan","landlady_informal",0.5,"He lifts sacks and hears everything. Useful on both counts.","Josta trades my rent for my ears. We both pretend it's about the sacks."),
E("odile_marsh","ilse_alder","mentor_apprentice",0.85,"The girl's the best hands I've trained. The Alders will simply have to cope.","She never praises. So when she almost does, I float home."),
E("odile_marsh","luce_tarn","quiet_trust",0.65,"The only one in this village who says less than necessary. Restful.","She fixed the winter fever and asked no questions. I pay those debts."),
E("odile_marsh","nan_weaver","old_friends",0.7,"She's hiding that cough. I'll give her one more week of pride.","Sixty years of friendship and she still can't let a woman die at her own pace."),
E("anselm","ilse_alder","teacher_fond",0.55,"The only borrower who returns books. And with questions in the margins.","Brother Anselm's shelf is the closest thing to the river towns I can reach."),
E("anselm","cormac_dunn","counsel",0.6,"He carries the village and won't set it down long enough to fix his own accounts.","Anselm means well. Meaning well is not a levy policy."),
E("petra_quill","dane_ferrin","commercial_allies",0.6,"His river prices are my winter margin, if he's not embellishing.","Petra's the only one here who thinks past the next market day."),
E("petra_quill","cormac_dunn","wary",0.4,"He calls my ideas 'river-town notions' at the square. In front of customers.","She'd redo the village in a season if we let her. Some of it maybe should be."),
E("mira_fenn","cormac_dunn","unspoken",0.45,"His mending is done early. That means nothing. Probably.","I find reasons to pass Fenn Cottage. A reeve should have better reasons."),
E("mira_fenn","nan_weaver","kin_informal",0.6,"She weaves, I sew, and she knew my mother. Some afternoons that's everything.","Her mother's needle, her mother's stubbornness. Good stock, sad eyes."),
E("luce_tarn","fenwick_roan","odd_pair",0.4,"He talks enough for both of us. Somehow it isn't tiring.","Luce is the only one who doesn't perform. I stop performing around her."),
E("bram_hale","cormac_dunn","tension_brewing",0.5,"The reeve can inspect my drainage when he pays his smith.","If I don't raise the drainage cut soon, the mill path floods and it becomes everyone's problem."),
E("maren_alder","odile_marsh","cordial_wary",0.5,"She's teaching my daughter something. I haven't decided what I think.","Maren will thank me in ten years. Or not. The girl matters more."),
E("fenwick_roan","sela_crane","friendly",0.5,"First stall that fed me when I turned up hungry. I don't forget it.","Feckless, but he turned up for the flood sandbags before anyone I actually pay."),
]

# ------------------------------------------------------------ write out ----
(CONTENT / "agents").mkdir(parents=True, exist_ok=True)
(CONTENT / "town.json").write_text(json.dumps(town, indent=2) + "\n")
(CONTENT / "relationships.json").write_text(json.dumps(
    {"notes": "Single edge list — the one place relationships are edited. "
              "closeness 0..1 is an interaction-propensity prior; views seed "
              "each agent's initial memories about the other.",
     "edges": relationships}, indent=2) + "\n")
for a in agents:
    (CONTENT / "agents" / f"{a['id']}.json").write_text(json.dumps(a, indent=2) + "\n")

print(f"wrote town.json, relationships.json ({len(relationships)} edges), "
      f"{len(agents)} agent seeds")
