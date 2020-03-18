from googletrans import Translator
import re
import demoji


time_fix_re = re.compile("((\d): (\d))")


class GoogleTranslator:
    def translate_from_bel(self, text):
        text = demoji.replace(text, " ")
        translator = Translator()
        lan = translator.detect(text).lang
        if lan != 'be':
            return text
        result = translator.translate(text, src='be', dest='ru')
        translated_text = result.text
        for whole, first_digit, second_digit in time_fix_re.findall(translated_text):
            translated_text = translated_text.replace(whole, "%s:%s" % (first_digit, second_digit))
        return translated_text
