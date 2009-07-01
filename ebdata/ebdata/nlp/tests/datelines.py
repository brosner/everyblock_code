from ebdata.nlp.datelines import guess_datelines
import unittest

class DatelineTestCase(unittest.TestCase):
    def assertDatelines(self, text, expected):
        self.assertEqual(guess_datelines(text), expected)

    def test_basic1(self):
        self.assertDatelines('CHICAGO -- Something happened', ['CHICAGO'])

    def test_basic2(self):
        self.assertDatelines('CHICAGO-- Something happened', ['CHICAGO'])

    def test_basic3(self):
        self.assertDatelines('CHICAGO --Something happened', ['CHICAGO'])

    def test_basic4(self):
        self.assertDatelines('CHICAGO--Something happened', ['CHICAGO'])

    def test_lowercase1(self):
        self.assertDatelines('chicago -- Something happened', [])

    def test_lowercase2(self):
        self.assertDatelines('That was in Chicago -- where something happened', [])

    def test_emdash1(self):
        self.assertDatelines('CHICAGO\x97Something happened', ['CHICAGO'])

    def test_emdash2(self):
        self.assertDatelines('CHICAGO \x97Something happened', ['CHICAGO'])

    def test_emdash3(self):
        self.assertDatelines('CHICAGO  \x97Something happened', ['CHICAGO'])

    def test_emdash4(self):
        self.assertDatelines(u'CHICAGO \u2015 Something happened', ['CHICAGO'])

    def test_emdash5(self):
        self.assertDatelines(u'CHICAGO\xa0--\xa0Something happened', ['CHICAGO'])

    def test_emdash6(self):
        self.assertDatelines(u'CHICAGO \xa0--\xa0 Something happened', ['CHICAGO'])

    def test_html_entity_dash1(self):
        self.assertDatelines('CHICAGO &#8213; Something happened', ['CHICAGO'])

    def test_html_entity_dash2(self):
        self.assertDatelines('CHICAGO &#151; Something happened', ['CHICAGO'])

    def test_html_entity_dash3(self):
        self.assertDatelines('CHICAGO &#x97; Something happened', ['CHICAGO'])

    def test_multi_word_dateline1(self):
        self.assertDatelines('SAN FRANCISCO -- Something happened', ['SAN FRANCISCO'])

    def test_multi_word_dateline2(self):
        self.assertDatelines('SOUTH SAN FRANCISCO -- Something happened', ['SOUTH SAN FRANCISCO'])

    def test_comma_periods(self):
        self.assertDatelines('CHESTERFIELD, S.C. -- Something happened', ['CHESTERFIELD, S.C.'])

    def test_comma_no_space(self):
        self.assertDatelines('CHESTERFIELD,S.C. -- Something happened', [])

    def test_lowercase(self):
        self.assertDatelines('Lowercase -- Something happened', [])

    def test_start_of_line1(self):
        self.assertDatelines('blah blah\nCHICAGO -- Something happened', ['CHICAGO'])

    def test_start_of_line2(self):
        self.assertDatelines('blah blah\n<b>CHICAGO -- Something happened', ['CHICAGO'])

    def test_start_of_line_p(self):
        self.assertDatelines('<div>BY ASSOCIATED PRESS</div><p>CHICAGO -- Something happened', ['CHICAGO'])

    def test_start_of_line_div(self):
        self.assertDatelines('<div>BY ASSOCIATED PRESS</div><div>CHICAGO -- Something happened', ['CHICAGO'])

    def test_start_of_line_div_then_more1(self):
        self.assertDatelines('<div><span>CHICAGO -- </span>Something happened', ['CHICAGO'])

    def test_start_of_line_div_then_more2(self):
        self.assertDatelines('<br><div><span>CHICAGO -- </span>Something happened', ['CHICAGO'])

    def test_start_of_line_div_then_more3(self):
        self.assertDatelines('<div> Reporting<br>Rafael Romo </div> <span> CHICAGO -- </span> Something happened', ['CHICAGO'])

    def test_second_word_lowercase(self):
        self.assertDatelines('Associated Press Writer<br><br><div>KANDAHAR, Afghanistan -- Something happened', ['KANDAHAR, Afghanistan'])

    def test_news_outlet_1(self):
        self.assertDatelines('CHICAGO (Aurora Beacon News) -- Something happened', ['CHICAGO'])

    def test_news_outlet_2(self):
        self.assertDatelines('CHICAGO (STNG) -- Something happened', ['CHICAGO'])

    def test_news_outlet_3(self):
        self.assertDatelines('CHICAGO (CBS) -- Something happened', ['CHICAGO'])

    def test_news_outlet_4(self):
        self.assertDatelines('CHICAGO (ABC) -- Something happened', ['CHICAGO'])

    def test_news_outlet_5(self):
        self.assertDatelines('CHICAGO (FOX) -- Something happened', ['CHICAGO'])

    def test_news_outlet_6(self):
        self.assertDatelines('CHICAGO (AP) -- Something happened', ['CHICAGO'])

    def test_news_outlet_7(self):
        self.assertDatelines('CHICAGO (Associated Press) -- Something happened', ['CHICAGO'])

    def test_news_outlet_8(self):
        self.assertDatelines('CHICAGO (Post-Tribune) -- Something happened', ['CHICAGO'])

    def test_news_outlet_9(self):
        self.assertDatelines('CHICAGO (Chicago Sun-Times) -- Something happened', ['CHICAGO'])

    def test_news_outlet_10(self):
        self.assertDatelines('CHICAGO (Chicago Tribune) -- Something happened', ['CHICAGO'])

    def test_news_outlet_11(self):
        self.assertDatelines('CHICAGO (Sports Network) -- Something happened', ['CHICAGO'])

    def test_news_outlet_12(self):
        self.assertDatelines('CHICAGO (BCN) -- Something happened', ['CHICAGO'])

    def test_timestamp_prefix1(self):
        self.assertDatelines('(07-17) 13:09 PDT BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix2(self):
        self.assertDatelines('(07-17) 13:09 MDT BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix3(self):
        self.assertDatelines('(07-17) 13:09 CDT BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix4(self):
        self.assertDatelines('(07-17) 13:09 EDT BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix5(self):
        self.assertDatelines('(07-17) 13:09 PST BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix6(self):
        self.assertDatelines('(07-17) 13:09 MST BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix7(self):
        self.assertDatelines('(07-17) 13:09 CST BERKELEY -- Something happened', ['BERKELEY'])

    def test_timestamp_prefix8(self):
        self.assertDatelines('(07-17) 13:09 EST BERKELEY -- Something happened', ['BERKELEY'])

if __name__ == "__main__":
    unittest.main()
