import discord
import asyncio
from typing import List, Dict, Tuple, Optional, Iterable
from enum import Enum

from constant.emoji import NB, LETTER
from util.function import get_member_in_channel
from util.exception import InvalidArgs
from .Leaders import leaders
from .Draft import BlindDraft, get_draft, draw_draft
from .constant import TURKEY

DRAFT_MODE_TITLE = "Mode de draft"
class DraftMode(Enum):
    WITH_TRADE = "Trade autorisé"
    NO_TRADE = "Trade interdit"
    BLIND = "Aveugle"
    RANDOM = "All Random"

EMOJI = str
VOTED_SETTINGS : Dict[str, List[Tuple[EMOJI, str]]] = {
    "Map": [(LETTER.P, "Pangée"), (LETTER.C, "Contient & Iles"), (NB[7], "7 mers"), (LETTER.L, "Lacs"), (LETTER.A, "Archipelle"), (LETTER.F, "Fractale"),
            ("🏝️", "Plateau d'ile"), ("🌋", "Primordial"), (LETTER.T, "Tilted Axis"), (LETTER.M, "Mer Intérieure"), ("🌍", "Terre"), ("❓", "Aléatoire")],
    "Diplo": [("🦄", "Normal Diplo"), ("➕", "Diplo +"), ("🦅", "Always War"), ("🐨", "Always Peace")],
    "Timer": [("🕑", "Dynamique"), ("⏩", "Compétitif"), ("🔥", "90s"), ("🦘", "Sephi n+30"), ("🇿", "ZLAN")],
    "Age du monde": [("🗻", "Normal"), ("🌋", "Nouveau")],
    "Nukes": [("☢️", "Autorisées"), ("⛔", "Interdites")],
    "Ressources": [(LETTER.C, "Classique"), (LETTER.A, "Abondante")],
    "Stratégiques": [(LETTER.C, "Classique"), (LETTER.A, "Abondante"), (LETTER.E, "Epique"), (LETTER.G, "Garentie")],
    "Ridges definition": [(LETTER.S, "Standard"), (LETTER.V, "Vanilla"), (LETTER.L, "Large opening"), (LETTER.I, "Impénétrable")],
    "Catastrophe": [(NB[0], "0"), (NB[1], "1"), (NB[2], "2"), (NB[3], "3"), (NB[4], "4")],
    DRAFT_MODE_TITLE: [("✅", DraftMode.WithTrade.value), ("🚫", DraftMode.NoTrade.value), ("🙈", "Aveugle"), ("❓", "All Random")]
}

class Voting:
    def __init__(self, members):
        self.members = members
        self.members_id = [i.id for i in members]
        self.waiting_members = self.members_id[:]
        self.result = {i: None for i in VOTED_SETTINGS}
        self.majority = len(self.members) // 2 + 1
        self.banned_leaders = []
        self.draft_mode = None

    async def run(self, channel : discord.TextChannel, client : discord.Client):
        await channel.send("Liste des joueurs: " + ' '.join(i.mention for i in self.members))
        sended = await asyncio.gather(*[self.send_line(k, v, channel) for k, v in VOTED_SETTINGS.items()])
        ban_msg = await self.send_ban_msg(channel)
        confirm_msg = await self.send_confirm_msg(channel)
        votes_msg_ids = [i.id for i in sended]
        msg_ids = votes_msg_ids
        msg_to_vote : Dict[int, Tuple[str, List[Tuple[EMOJI, str]]]] = {sended[i].id: (name, v) for i, (name, (k, v)) in enumerate(VOTED_SETTINGS.items())}
        await asyncio.gather(*[self.add_reactions(msg, (i[0] for i in v)) for msg, v in zip(sended, VOTED_SETTINGS.values())])

        def check(reac_ : discord.Reaction, user_ : discord.User):
            return reac_.message.id in msg_ids

        while True:
            reaction, user = await client.wait_for('reaction_add', check=check, timeout=600)  # type: (discord.Reaction, discord.User)
            if user.id not in self.members_id:
                try:
                    await reaction.remove(user)
                except discord.HTTPException:
                    pass
                continue
            if reaction.message.id == confirm_msg.id and user.id in self.waiting_members:
                self.waiting_members.remove(user.id)
                if not self.waiting_members:
                    break
            elif reaction.message.id == ban_msg.id:
                emoji : discord.Emoji = reaction.emoji
                if not isinstance(emoji, discord.Emoji):
                    continue
                leader = leaders.get_leader_by_emoji_id(reaction.emoji.id)
                if not leader:
                    continue
                if self.is_vote_winner(reaction) and leader not in self.banned_leaders:
                    self.banned_leaders.append(leader)
            elif reaction.message.id in votes_msg_ids and self.is_vote_winner(reaction):
                winner = self.get_winner_by_emoji_str(str(reaction.emoji), msg_to_vote[reaction.message.id])
                if not winner:
                    continue
                msg : discord.Message = reaction.message
                await asyncio.gather(msg.clear_reactions(), msg.edit(content="__**{0[0]}**__: {0[1]} {0[2]}".format(winner)))
                if winner[0] == DRAFT_MODE_TITLE:
                    self.draft_mode = DraftMode(winner[2])

        # Run draft
        if not self.draft_mode:
            await channel.send("WARNING : Aucun mode de draft n'a été voté, une draft FFA classique va donc être lancé.")
            self.draft_mode = DraftMode.NO_TRADE
        if self.draft_mode in (DraftMode.NO_TRADE, DraftMode.WITH_TRADE):
            drafts = get_draft(len(self.members), '.'.join(str(i) for i in self.banned_leaders), client=client)
            await draw_draft(drafts, (m.mention for m in self.members), channel)
            return
        if self.draft_mode == DraftMode.RANDOM:
            await channel.send("Le mode de draft sélectionné étant All Random, la draft est terminé !")
            return
        if self.draft_mode == DraftMode.BLIND:
            draft = BlindDraft(self.members, '.'.join(str(i) for i in self.banned_leaders))
            await draft.run(channel, client)
            return




    @staticmethod
    async def send_ban_msg(channel) -> discord.Message:
        msg = await channel.send("__**Bans**__: Sélectionnez les civs à bannir depuis la liste des emojis.")
        await msg.add_reaction("🚫")
        return msg

    async def send_confirm_msg(self, channel) -> discord.Message:
        msg = await channel.send("En attente de : " + ', '.join(f"<@{i}>" for i in self.waiting_members))
        await msg.add_reaction(TURKEY)
        return msg

    async def edit_confirm_msg(self, msg):
        await msg.edit("En attente de : " + ', '.join(f"<@{i}>" for i in self.waiting_members))

    async def is_vote_winner(self, reaction : discord.Reaction) -> bool:
        ls = list(filter(lambda user: user.id in self.members_id, await reaction.users().flatten))
        if len(ls) >= self.majority:
            return True
        return False

    @staticmethod
    async def send_line(name, line, channel):
        return await channel.send(f"__**{name}**__:" + ', '.join(f"{i}={j}" for i, j in line))

    @staticmethod
    async def add_reactions(msg : discord.Message, reactions : Iterable[str]):
        for reaction in reactions:
            await msg.add_reaction(reaction)

    def get_winner_by_emoji_str(self, reaction_str : EMOJI, vote : Tuple[str, Iterable[Tuple[EMOJI, str]]]) -> Optional[Tuple[str, EMOJI, str]]:
        for line in vote[1]:
            if line[0] == reaction_str:
                return (vote[0], *line)
        return None


class CmdCivFRVoting:
    async def cmd_vote(self, *args, member, message : discord.Message, channel, client, **_):
        if not args:
            members = get_member_in_channel(member.voice)
        else:
            members = message.mentions
            if not members:
                raise InvalidArgs("Vous devez sois laisser la commande vide, ou bien notifier chacune des personnes participant au vote")
        voting = Voting(members)
        await voting.run(channel, client)
