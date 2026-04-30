import logging

from pathlib import Path
from typing import Union, List
from configparser import ConfigParser, SectionProxy, Error as ConfigParserError
logger = logging.getLogger('debug')


class Emotes:
    """
    Represents a list of emotes read in from a character INI file
    used for validating which emotes can be sent by clients.
    """
    REQUIRED_INI_SECTIONS = ['Options', 'Emotions']
    VALID_EMOTION_SECTIONS = ['number']

    def __init__(self, name: str):
        self.CHAR_DIR = 'characters'
        self.name = name
        self.emotes = set()

        self._add_emotes()

    @classmethod
    def _has_valid_ini_sections(cls, char_ini: ConfigParser) -> bool:
        ini_sections = char_ini.sections()
        return all(key in ini_sections for key in cls.REQUIRED_INI_SECTIONS)

    @classmethod
    def _is_valid_emotions_section(cls, emotes_section: SectionProxy) -> bool:
        emotions_sections = emotes_section.keys()
        return all(key in emotions_sections for key in cls.VALID_EMOTION_SECTIONS)

    @staticmethod
    def _create_config_parser() -> ConfigParser:
        return ConfigParser(comment_prefixes=('#', ';', '//', '\\\\'),
                            strict=False,
                            allow_no_value=True)

    def _read_ini(self) -> Union[ConfigParser, None]:
        char_ini = self._create_config_parser()

        char_path = Path(self.CHAR_DIR, self.name, 'char.ini')
        if char_path.exists():
            try:
                with open(char_path, encoding='utf-8') as file:
                    char_ini.read_file(file)
            except ConfigParserError as exc:
                logger.warning(f'Failed to parse {char_path}: {exc}')
                return None
            if self._has_valid_ini_sections(char_ini):
                return char_ini
            else:
                logger.warning(f'{char_path} does not have the required sections')
        else:
            logger.warning(f'Character file {char_path} not found')

        return None

    def _add_emotes(self):
        char_ini = self._read_ini()
        if char_ini is not None:
            if self._is_valid_emotions_section(char_ini['Emotions']) is False:
                logger.warning('Emotions needs a number section')
                return

            total_char_emotions = char_ini['Emotions'].getint('number')
            number_of_emotions = range(1, total_char_emotions + 1)

            emote_ids = [str(emote_id) for emote_id in number_of_emotions]
            self._create_emotes(emote_ids, char_ini)

    def _create_emotes(self, emote_ids: List[str], char_ini: ConfigParser):
        for emote_id in emote_ids:
            emotion_information = char_ini['Emotions'].get(emote_id)
            if emotion_information is not None:
                _name, preanim, anim, _mod = emotion_information.split('#')[
                    :4]
                sfx = self._get_sfx(emote_id, char_ini)
                self.emotes.add((preanim, anim, sfx))

                # No SFX should always be allowed
                self.emotes.add((preanim, anim, None))

    @staticmethod
    def _get_sfx(emote_id: str, char_ini: ConfigParser) -> Union[str, None]:
        if 'SoundN' not in char_ini or emote_id not in char_ini['SoundN']:
            return None

        sfx = char_ini['SoundN'][emote_id]
        if len(sfx) == 1:
            # Often, a one-character SFX is a placeholder for no sfx,
            # so allow it
            sfx = None
        return sfx

    def validate(self, preanim: str, anim: str, sfx: Union[str, None]) -> bool:
        """
        Determines whether or not an emote canonically belongs to this
        character (that is, it is defined server-side).
        """
        # There are no emotes loaded, so allow anything
        if len(self.emotes) == 0:
            return True

        if sfx is not None and len(sfx) <= 1:
            sfx = None
        return (preanim, anim, sfx) in self.emotes
