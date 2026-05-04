"""
CAIQ-PANAS item bank and session-version routing (Portuguese copy).
Full = sessions 1, 5, 9 (29 items). Mini = sessions 2,3,4,6,7,8 (10 items).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Literal, Sequence

SurveyVersion = Literal["full", "mini"]

SLOTS_PER_WEEK = 3


@dataclass(frozen=True)
class SurveyItem:
    item_id: str
    text: str
    block: Literal["caiq", "panas"]


CAIQ_INSTRUCTION = (
    "Pensa na sessão de hoje em relação à tua interação. "
    "Diz-nos quanto concordas com cada frase. Não há respostas certas nem erradas."
)

CAIQ_SCALE_HEADER = (
    "Discordo totalmente 😩      Discordo 🙁      Nem concordo nem discordo 😐      "
    "Concordo 🙂      Concordo totalmente 😄"
)

CAIQ_ROW_EMOJIS = "😩     🙁     😐     🙂      😄"

PANAS_INSTRUCTION = "Durante a sessão de leitura de hoje, eu senti-me..."

PANAS_SCALE_HEADER = (
    "1 (Nada ou muito pouco)  2 (Um pouco)  3 (Moderadamente)  4 (Bastante)  5 (Muitíssimo)"
)

# 19 CAIQ items (deduplicated full instrument)
CAIQ_FULL_ITEMS: List[SurveyItem] = [
    SurveyItem("CAIQ_01", "Senti que estava no mesmo espaço que o meu companheiro de leitura.", "caiq"),
    SurveyItem("CAIQ_02", "Senti que o meu companheiro de leitura prestou atenção a mim.", "caiq"),
    SurveyItem("CAIQ_03", "Senti que o meu companheiro de leitura notou quando eu precisava de ajuda.", "caiq"),
    SurveyItem("CAIQ_04", "Senti que o meu companheiro de leitura prestou atenção àquilo que eu estava a ler.", "caiq"),
    SurveyItem("CAIQ_05", "Sinto-me confortável perto do meu companheiro de leitura.", "caiq"),
    SurveyItem("CAIQ_06", "O meu companheiro de leitura parece um amigo para mim.", "caiq"),
    SurveyItem("CAIQ_07", "Sinto que posso confiar no meu companheiro de leitura.", "caiq"),
    SurveyItem("CAIQ_08", "Sinto que o meu companheiro de leitura é de confiança.", "caiq"),
    SurveyItem("CAIQ_09", "Tenho confiança de que a informação da conversa é verdadeira.", "caiq"),
    SurveyItem("CAIQ_10", "Se eu estivesse em apuros, o meu companheiro de leitura estaria disposto a ajudar-me.", "caiq"),
    SurveyItem("CAIQ_11", "O meu companheiro de leitura respondeu às minhas perguntas de forma relevante.", "caiq"),
    SurveyItem("CAIQ_12", "Quando fazia perguntas, o meu companheiro de leitura respondia rapidamente.", "caiq"),
    SurveyItem("CAIQ_13", "Senti que podia escolher quando pedir ajuda ao companheiro.", "caiq"),
    SurveyItem("CAIQ_14", "O companheiro deixou-me ler ao meu próprio ritmo.", "caiq"),
    SurveyItem("CAIQ_15", "Gostaria de interagir com o meu companheiro de leitura novamente.", "caiq"),
    SurveyItem("CAIQ_16", "Gostaria de voltar a ver o meu companheiro de leitura.", "caiq"),
    SurveyItem("CAIQ_17", "As respostas do meu companheiro de leitura foram ajustadas para mim.", "caiq"),
    SurveyItem("CAIQ_18", "As respostas pareciam basear-se no que eu gosto ou disse antes.", "caiq"),
    SurveyItem("CAIQ_19", "O companheiro parecia saber coisas sobre mim.", "caiq"),
]

# PANAS full: PA1–PA5, NA1–NA5
PANAS_FULL_ITEMS: List[SurveyItem] = [
    SurveyItem("PANAS_PA1", "Alegre", "panas"),
    SurveyItem("PANAS_PA2", "Animado/a", "panas"),
    SurveyItem("PANAS_PA3", "Feliz", "panas"),
    SurveyItem("PANAS_PA4", "Cheio/a de energia", "panas"),
    SurveyItem("PANAS_PA5", "Orgulhoso/a", "panas"),
    SurveyItem("PANAS_NA1", "Infeliz", "panas"),
    SurveyItem("PANAS_NA2", "Zangado/a", "panas"),
    SurveyItem("PANAS_NA3", "Com medo", "panas"),
    SurveyItem("PANAS_NA4", "Assustado/a", "panas"),
    SurveyItem("PANAS_NA5", "Triste", "panas"),
]

# Mini: 6 CAIQ (subset of full ids)
MINI_CAIQ_IDS: Sequence[str] = (
    "CAIQ_02",
    "CAIQ_06",
    "CAIQ_11",
    "CAIQ_13",
    "CAIQ_15",
    "CAIQ_17",
)

# Mini PANAS: PA2, PA3, NA4, NA5 per scoring spec
MINI_PANAS_IDS: Sequence[str] = ("PANAS_PA2", "PANAS_PA3", "PANAS_NA4", "PANAS_NA5")

_FULL_IDS = frozenset({1, 5, 9})


def linear_session_number(week_index: int, slot_index: int) -> int:
    return (week_index - 1) * SLOTS_PER_WEEK + slot_index


def survey_version_for_session(week_index: int, slot_index: int) -> SurveyVersion | None:
    n = linear_session_number(week_index, slot_index)
    if n in _FULL_IDS:
        return "full"
    if 1 <= n <= 9 and n not in _FULL_IDS:
        return "mini"
    return None


def expected_item_ids(version: SurveyVersion) -> List[str]:
    if version == "full":
        return [i.item_id for i in CAIQ_FULL_ITEMS] + [i.item_id for i in PANAS_FULL_ITEMS]
    return list(MINI_CAIQ_IDS) + list(MINI_PANAS_IDS)


def survey_items_for_version(version: SurveyVersion) -> List[SurveyItem]:
    if version == "full":
        return list(CAIQ_FULL_ITEMS) + list(PANAS_FULL_ITEMS)
    id_to_item = {it.item_id: it for it in CAIQ_FULL_ITEMS + PANAS_FULL_ITEMS}
    out: List[SurveyItem] = []
    for iid in expected_item_ids(version):
        out.append(id_to_item[iid])
    return out


def survey_definition_payload(version: SurveyVersion) -> dict:
    items = survey_items_for_version(version)
    return {
        "surveyVersion": version,
        "caiqInstruction": CAIQ_INSTRUCTION,
        "caiqScaleHeader": CAIQ_SCALE_HEADER,
        "caiqRowEmojis": CAIQ_ROW_EMOJIS,
        "panasInstruction": PANAS_INSTRUCTION,
        "panasScaleHeader": PANAS_SCALE_HEADER,
        "items": [
            {
                "itemId": it.item_id,
                "text": it.text,
                "block": it.block,
            }
            for it in items
        ],
    }
