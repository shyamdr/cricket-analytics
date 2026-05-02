"""Match summary narrative generator.

Produces a 300-500 character match summary from structured match data
using a large pool of sentence templates. Templates are selected based
on match scenario (big knock, bowling spell, close finish, etc.) and
deterministically randomized per match_id so the same match always
produces the same summary.
"""

from __future__ import annotations

import hashlib


def _seed(match_id: str) -> int:
    """Deterministic seed from match_id so same match = same template pick."""
    return int(hashlib.md5(match_id.encode()).hexdigest()[:8], 16)


def _pick(templates: list[str], match_id: str, offset: int = 0) -> str:
    """Pick a template deterministically from a list."""
    idx = (_seed(match_id) + offset) % len(templates)
    return templates[idx]


# ---------------------------------------------------------------------------
# Template pools — {var} placeholders filled by .format()
# ---------------------------------------------------------------------------

# Opening sentences — batting hero (50+ by winning team's top scorer)
_BATTING_HERO = [
    "{batter}'s magnificent {runs} off {balls} balls (SR {sr}) powered {winner} to a convincing {margin} victory over {loser}.",
    "A scintillating {runs} off {balls} deliveries by {batter} proved to be the difference as {winner} cruised past {loser} by {margin}.",
    "{batter} smashed a sensational {runs} off just {balls} balls at a strike rate of {sr}, steering {winner} to a {margin} win against {loser}.",
    "It was the {batter} show as a blistering {runs}({balls}) knock handed {winner} a comfortable {margin} triumph over {loser}.",
    "{winner} rode on {batter}'s explosive {runs} off {balls} balls to overpower {loser} by {margin} in a one-sided affair.",
    "A masterclass from {batter} — {runs} runs off {balls} balls with a strike rate of {sr} — was the cornerstone of {winner}'s {margin} victory.",
    "{batter} lit up the ground with a breathtaking {runs} off {balls} deliveries, propelling {winner} to a dominant {margin} win over {loser}.",
    "The match belonged to {batter}, whose stunning {runs}({balls}) innings at {sr} SR left {loser} with no answers as {winner} won by {margin}.",
    "{batter} played the innings of the match — {runs} off {balls} balls — as {winner} chased down the target with {margin} to spare.",
    "{winner} had {batter} to thank for a match-winning {runs} off {balls} deliveries that sealed a {margin} victory against {loser}.",
]

# Opening sentences — bowling hero (3+ wickets by winning team's bowler)
_BOWLING_HERO = [
    "{bowler} ripped through {loser}'s batting with figures of {wkts}/{conc}, spearheading {winner}'s {margin} victory.",
    "A devastating spell of {wkts}/{conc} by {bowler} dismantled {loser}'s lineup as {winner} romped home by {margin}.",
    "{bowler}'s match-winning {wkts}/{conc} left {loser} in tatters, paving the way for {winner}'s {margin} triumph.",
    "{winner} owe their {margin} win to {bowler}'s brilliant {wkts}/{conc} that broke the back of {loser}'s innings.",
    "It was {bowler}'s day with the ball — {wkts}/{conc} — as {winner} dismantled {loser} to win by {margin}.",
    "{bowler} was virtually unplayable, returning {wkts}/{conc} to hand {winner} a comprehensive {margin} win over {loser}.",
    "The {bowler} spell of {wkts}/{conc} was the turning point as {winner} overwhelmed {loser} by {margin}.",
    "{loser} had no answer to {bowler}'s fiery {wkts}/{conc} as {winner} sealed a {margin} victory with ease.",
]

# Opening sentences — POM led (generic, when no standout 50 or 3-fer)
_POM_LED = [
    "{pom} delivered an all-round performance to earn the Player of the Match award as {winner} beat {loser} by {margin}.",
    "A fine display from {pom} was the highlight as {winner} edged past {loser} in a {margin} victory.",
    "{pom} rose to the occasion, guiding {winner} to a hard-fought {margin} win over {loser}.",
    "{winner} prevailed by {margin} against {loser}, with {pom} playing a pivotal role throughout the contest.",
    "It was {pom}'s match to remember as {winner} outplayed {loser} by {margin} in an entertaining encounter.",
    "{pom} stamped authority on the game, leading {winner} to a {margin} victory that {loser} will want to forget quickly.",
]

# Opening sentences — generic (no standout performer)
_GENERIC_WIN = [
    "{winner} put together a complete team performance to beat {loser} by {margin} in a well-contested match.",
    "A disciplined effort across departments saw {winner} overcome {loser} by {margin}.",
    "{winner} proved too strong for {loser}, securing a {margin} victory in a clinical display.",
    "Contributions from across the lineup helped {winner} register a {margin} win against {loser}.",
    "{loser} were outplayed in all facets as {winner} coasted to a {margin} victory.",
    "{winner} ticked all the boxes to record a {margin} win over {loser} in a professional outing.",
]

# Middle sentences — losing team's top scorer fought
_LOSER_FOUGHT = [
    "{batter}'s gutsy {runs} off {balls} balls gave {loser} hope, but it ultimately proved insufficient.",
    "Despite {batter}'s valiant {runs}({balls}), {loser} couldn't get over the line.",
    "{batter} waged a lone battle with {runs} off {balls} balls for {loser}, but lacked support from the other end.",
    "A fighting {runs} from {batter} kept {loser} in the hunt briefly, but the required rate proved too steep.",
    "{loser} had {batter}'s {runs} off {balls} balls to show for their effort, but it was never quite enough.",
    "The only resistance for {loser} came from {batter}, who scored a determined {runs} off {balls} deliveries.",
]

# Middle sentences — losing team's bowler tried
_LOSER_BOWLER = [
    "{bowler} gave it everything with {wkts} wickets for {loser}, but the batting let them down.",
    "{bowler}'s {wkts}-wicket haul was a silver lining for {loser} in an otherwise disappointing outing.",
    "While {bowler} claimed {wkts} wickets, {loser}'s other bowlers failed to build pressure.",
    "{loser} will take heart from {bowler}'s {wkts} wickets, even though the result didn't go their way.",
]

# Flavor sentences — dropped catches
_DROPPED_CATCHES = [
    "Sloppy fielding didn't help either, with {count} dropped catch{es} that could have changed the complexion of the game.",
    "The fielding was below par — {count} catch{es} went down, letting key batters off the hook at crucial moments.",
    "{count} dropped catch{es} proved costly, giving the opposition extra lives when it mattered most.",
    "It was a day to forget in the field with {count} catch{es} put down, adding to the frustration.",
]

# Flavor sentences — POM mention (when not already the hero)
_POM_MENTION = [
    "{pom} was deservedly named Player of the Match for the all-round contribution.",
    "{pom} took home the Player of the Match award after a decisive performance.",
    "The Player of the Match award went to {pom} for the match-defining effort.",
]

# No result
_NO_RESULT = [
    "The match was abandoned without a result as rain played spoilsport, denying both teams a chance to compete.",
    "Play was called off without a ball being bowled, leaving both teams frustrated as weather had the final say.",
    "The contest ended without a result after persistent interruptions prevented a fair game from taking place.",
]


def generate_match_summary(
    match_id: str,
    winner: str | None,
    loser: str,
    margin: str | None,
    pom: str | None,
    top_scorers: dict,
    top_bowlers: dict,
    drop_count: int,
) -> str:
    """Generate a 300-500 char match narrative from templates.

    Args:
        match_id: Cricsheet match ID (used as deterministic seed).
        winner: Winning team name (None if no result).
        loser: Losing team name.
        margin: Winning margin text (e.g. "7 wickets").
        pom: Player of the match name.
        top_scorers: Dict of {team_name: {batter, runs, balls, fours, sixes}}.
        top_bowlers: Dict of {team_name: {bowler, wickets, runs_conceded, overs}}.
        drop_count: Number of dropped catches in the match.

    Returns:
        Summary string, 300-500 characters.
    """
    if not winner or not margin:
        return _pick(_NO_RESULT, match_id)

    ws = top_scorers.get(winner) or {}
    ls = top_scorers.get(loser) or {}
    wb = top_bowlers.get(winner) or {}
    lb = top_bowlers.get(loser) or {}

    parts: list[str] = []

    # --- Opening sentence ---
    if ws.get("runs", 0) >= 50:
        sr = round(ws["runs"] * 100 / max(ws.get("balls", 1), 1))
        parts.append(
            _pick(_BATTING_HERO, match_id).format(
                batter=ws["batter"],
                runs=ws["runs"],
                balls=ws["balls"],
                sr=sr,
                winner=winner,
                loser=loser,
                margin=margin,
            )
        )
    elif wb.get("wickets", 0) >= 3:
        parts.append(
            _pick(_BOWLING_HERO, match_id).format(
                bowler=wb["bowler"],
                wkts=wb["wickets"],
                conc=wb["runs_conceded"],
                winner=winner,
                loser=loser,
                margin=margin,
            )
        )
    elif pom:
        parts.append(
            _pick(_POM_LED, match_id).format(pom=pom, winner=winner, loser=loser, margin=margin)
        )
    else:
        parts.append(
            _pick(_GENERIC_WIN, match_id).format(winner=winner, loser=loser, margin=margin)
        )

    # --- Middle: losing team's batter ---
    if ls.get("runs", 0) >= 30 and len(" ".join(parts)) < 320:
        parts.append(
            _pick(_LOSER_FOUGHT, match_id, offset=1).format(
                batter=ls["batter"],
                runs=ls["runs"],
                balls=ls["balls"],
                loser=loser,
            )
        )

    # --- Middle: losing team's bowler ---
    if lb.get("wickets", 0) >= 2 and len(" ".join(parts)) < 370:
        parts.append(
            _pick(_LOSER_BOWLER, match_id, offset=2).format(
                bowler=lb["bowler"], wkts=lb["wickets"], loser=loser
            )
        )

    # --- Flavor: dropped catches ---
    if drop_count > 0 and len(" ".join(parts)) < 400:
        es = "es" if drop_count > 1 else ""
        parts.append(_pick(_DROPPED_CATCHES, match_id, offset=3).format(count=drop_count, es=es))

    # --- Flavor: POM if not already mentioned ---
    if pom and pom != ws.get("batter") and pom != wb.get("bowler") and len(" ".join(parts)) < 430:
        parts.append(_pick(_POM_MENTION, match_id, offset=4).format(pom=pom))

    text = " ".join(parts)

    # Enforce 500 char max
    if len(text) > 500:
        trimmed = text[:500]
        last_period = trimmed.rfind(".")
        text = trimmed[: last_period + 1] if last_period > 250 else trimmed[:497] + "..."

    return text
