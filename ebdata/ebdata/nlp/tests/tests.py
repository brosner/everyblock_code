# -*- coding: utf-8 -*-
from ebdata.nlp.addresses import parse_addresses
from ebdata.nlp.places import phrase_tagger
import unittest

class AddressParsing(unittest.TestCase):
    def assertParses(self, text, expected):
        self.assertEqual(parse_addresses(text), expected)

class MixedCaseAddressParsing(AddressParsing):
    def test_empty(self):
        self.assertParses('', [])

    def test_nomatch1(self):
        self.assertParses('Hello there', [])

    def test_nomatch2(self):
        self.assertParses('Call 321-FUN-TIMES', [])

    def test_nomatch3(self):
        self.assertParses('Call 321-Fun-Times', [])

    def test_nomatch4(self):
        self.assertParses('Call 321-Fun Times', [])

    def test_address_basic(self):
        self.assertParses('123 Main St.', [('123 Main St.', '')])

    def test_address_basic_in_sentence(self):
        self.assertParses('I live at 123 Main St., you know.', [('123 Main St.', '')])

    def test_address_basic_with_followup_sentence(self):
        self.assertParses('I live at 123 Main St. The other person lives elsewhere.', [('123 Main St.', '')])

    def test_address_no_suffix(self):
        self.assertParses('123 Main', [('123 Main', '')])

    def test_address_no_suffix_period(self):
        self.assertParses('Lives at 123 Main.', [('123 Main', '')])

    def test_address_multiple_spaces1(self):
        self.assertParses('123  Main St.', [('123  Main St.', '')])

    def test_address_multiple_spaces2(self):
        self.assertParses('123 Main  St.', [('123 Main  St.', '')])

    def test_address_dir_n(self):
        self.assertParses('123 N. Main St.', [('123 N. Main St.', '')])

    def test_address_dir_s(self):
        self.assertParses('123 S. Main St.', [('123 S. Main St.', '')])

    def test_address_dir_e(self):
        self.assertParses('123 E. Main St.', [('123 E. Main St.', '')])

    def test_address_dir_w(self):
        self.assertParses('123 W. Main St.', [('123 W. Main St.', '')])

    def test_address_dir_ne(self):
        self.assertParses('123 NE. Main St.', [('123 NE. Main St.', '')])

    def test_address_dir_nw(self):
        self.assertParses('123 NW. Main St.', [('123 NW. Main St.', '')])

    def test_address_dir_se(self):
        self.assertParses('123 SE. Main St.', [('123 SE. Main St.', '')])

    def test_address_dir_sw(self):
        self.assertParses('123 SW. Main St.', [('123 SW. Main St.', '')])

    def test_address_dir_ne_no_period(self):
        self.assertParses('123 NE Main St.', [('123 NE Main St.', '')])

    def test_address_dir_nw_no_period(self):
        self.assertParses('123 NW Main St.', [('123 NW Main St.', '')])

    def test_address_dir_se_no_period(self):
        self.assertParses('123 SE Main St.', [('123 SE Main St.', '')])

    def test_address_dir_sw_no_period(self):
        self.assertParses('123 SW Main St.', [('123 SW Main St.', '')])

    def test_address_dir_northeast(self):
        self.assertParses('123 Northeast Main St.', [('123 Northeast Main St.', '')])

    def test_address_dir_northwest(self):
        self.assertParses('123 Northwest Main St.', [('123 Northwest Main St.', '')])

    def test_address_dir_southeast(self):
        self.assertParses('123 Southeast Main St.', [('123 Southeast Main St.', '')])

    def test_address_dir_southwest(self):
        self.assertParses('123 Southwest Main St.', [('123 Southwest Main St.', '')])

    def test_address_dir_no_period(self):
        self.assertParses('123 N Main St.', [('123 N Main St.', '')])

    def test_address_coincidence(self):
        self.assertParses('My Favorite Number Is 123 And I Love It.', [('123 And', '')])

    def test_block_basic(self):
        self.assertParses('100 block of Main Street', [('100 block of Main Street', '')])

    def test_block_zero(self):
        self.assertParses('0 block of Main Street', [('0 block of Main Street', '')])

    def test_block_first(self):
        self.assertParses('first block of Main Street', [('first block of Main Street', '')])

    def test_block_first_cap(self):
        self.assertParses('First block of Main Street', [('First block of Main Street', '')])

    def test_block_with_direction_first_north(self):
        self.assertParses('800 North Block of Lawrence Avenue', [('800 North Block of Lawrence Avenue', '')])

    def test_block_with_direction_first_south(self):
        self.assertParses('800 South Block of Lawrence Avenue', [('800 South Block of Lawrence Avenue', '')])

    def test_block_with_direction_first_east(self):
        self.assertParses('800 East Block of Lawrence Avenue', [('800 East Block of Lawrence Avenue', '')])

    def test_block_with_direction_first_west(self):
        self.assertParses('800 West Block of Lawrence Avenue', [('800 West Block of Lawrence Avenue', '')])

    def test_block_no_suffix(self):
        self.assertParses('1000 block of Western', [('1000 block of Western', '')])

    def test_block_cap(self):
        self.assertParses('100 Block of Main Street', [('100 Block of Main Street', '')])

    def test_block_hyphen(self):
        self.assertParses('5700-block of South Indiana', [('5700-block of South Indiana', '')])

    def test_block_period_not_included(self):
        self.assertParses('It happened on the 1000 block of Western.', [('1000 block of Western', '')])

    def test_block_comma_not_included(self):
        self.assertParses('It happened on the 1000 block of Western, officials said', [('1000 block of Western', '')])

    def test_block_quote_not_included(self):
        self.assertParses('"It happened on the 1000 block of Western" they said.', [('1000 block of Western', '')])

    def test_block_no_double_zeroes(self):
        self.assertParses('Henry lives on the 140 block of Park Hill Avenue, right?', [('140 block of Park Hill Avenue', '')])

    def test_block_direction(self):
        self.assertParses('100 Block of N. Main Street', [('100 Block of N. Main Street', '')])

    def test_suffix_period_included(self):
        self.assertParses('The event at 1358 W. Leland Ave. was fun.', [('1358 W. Leland Ave.', '')])

    def test_multi_word_street_name(self):
        self.assertParses('Residents of 3200 N. Lake Shore Drive were happy.', [('3200 N. Lake Shore Drive', '')])

    def test_prefix_mc(self):
        self.assertParses('I live at 926 E. McLemore.', [('926 E. McLemore', '')])

    def test_prefix_st(self):
        self.assertParses('I live at 926 N. St. Louis.', [('926 N. St. Louis', '')])

    def test_prefix_st_no_period(self):
        self.assertParses('I live at 926 N. St Louis.', [('926 N. St Louis', '')])

    def test_prefix_st_no_period_suffix(self):
        self.assertParses('I live at 926 N. St Louis St.', [('926 N. St Louis St.', '')])

    def test_prefix_saint(self):
        self.assertParses('I live at 926 N. Saint Louis St.', [('926 N. Saint Louis St.', '')])

    def test_newlines_excluded1(self):
        self.assertParses('The number 926\nIs cool', [])

    def test_newlines_excluded2(self):
        self.assertParses('I live at 123\nMain St.', [])

    def test_address_range1(self):
        self.assertParses('10-12 Main St.', [('10-12 Main St.', '')])

    def test_address_range2(self):
        self.assertParses('10-12 N. Main St.', [('10-12 N. Main St.', '')])

    def test_address_range3(self):
        self.assertParses('0-100 Main St.', [('0-100 Main St.', '')])

    def test_address_range4(self):
        self.assertParses('0-100 N. Main St.', [('0-100 N. Main St.', '')])

    def test_pre_number_quote(self):
        self.assertParses('The address is "123 Main St."', [('123 Main St.', '')])

    def test_pre_number_dash(self):
        self.assertParses('I-90 Edens', [])

    def test_pre_number_dollar_sign(self):
        self.assertParses('Hawaii Gas Passes $5 Mark', [])

    def test_pre_number_letter(self):
        self.assertParses('A123 Main St.', [])

    def test_pre_number_slash(self):
        self.assertParses('Chicago 24/7 Crime', [])

    def test_pre_number_colon(self):
        self.assertParses('Happened at about 6:30 Wednesday night', [])

    def test_pre_number_comma(self):
        self.assertParses('That is worth more than $3,000 American dollars', [])

    def test_pre_number_period(self):
        self.assertParses('He received a 3.0 Grade Point Average', [])

    def test_mlk1(self):
        self.assertParses('3624 S. Dr. Martin Luther King Jr. Memorial Drive', [('3624 S. Dr. Martin Luther King Jr. Memorial Drive', '')])

    def test_mlk2(self):
        self.assertParses('3624 S. Dr. Martin Luther King, Jr., Memorial Drive', [('3624 S. Dr. Martin Luther King, Jr., Memorial Drive', '')])

    def test_mlk3(self):
        self.assertParses('3624 S. Dr. Martin Luther King, Jr. Memorial Drive', [('3624 S. Dr. Martin Luther King, Jr. Memorial Drive', '')])

    def test_mlk4(self):
        self.assertParses('3624 S. Martin Luther King, Jr., Memorial Drive', [('3624 S. Martin Luther King, Jr., Memorial Drive', '')])

    def test_mlk5(self):
        self.assertParses('3624 S. Dr. Martin Luther King Drive', [('3624 S. Dr. Martin Luther King Drive', '')])

    def test_mlk6(self):
        self.assertParses('3624 S. Dr. Martin Drive', [('3624 S. Dr. Martin Drive', '')])

    def test_junior1(self):
        self.assertParses('3624 S. John Hancock Jr. Road', [('3624 S. John Hancock Jr. Road', '')])

    def test_junior2(self):
        self.assertParses('3624 S. John Hancock, Jr., Road', [('3624 S. John Hancock, Jr., Road', '')])

    def test_numeric_street1(self):
        self.assertParses('330 West 95th Street', [('330 West 95th Street', '')])

    def test_numeric_street2(self):
        self.assertParses('the Continental, located at 330 West 95th Street.', [('330 West 95th Street', '')])

    def test_suffix_ave(self):
        self.assertParses('The man at 123 Main Ave. was cool.', [('123 Main Ave.', '')])

    def test_suffix_blvd(self):
        self.assertParses('The man at 123 Main Blvd. was cool.', [('123 Main Blvd.', '')])

    def test_suffix_bvd(self):
        self.assertParses('The man at 123 Main Bvd. was cool.', [('123 Main Bvd.', '')])

    def test_suffix_cir(self):
        self.assertParses('The man at 123 Main Cir. was cool.', [('123 Main Cir.', '')])

    def test_suffix_ct(self):
        self.assertParses('The man at 123 Main Ct. was cool.', [('123 Main Ct.', '')])

    def test_suffix_dr(self):
        self.assertParses('The man at 123 Main Dr. was cool.', [('123 Main Dr.', '')])

    def test_suffix_ln(self):
        self.assertParses('The man at 123 Main Ln. was cool.', [('123 Main Ln.', '')])

    def test_suffix_pkwy(self):
        self.assertParses('The man at 123 Main Pkwy. was cool.', [('123 Main Pkwy.', '')])

    def test_suffix_pl(self):
        self.assertParses('The man at 123 Main Pl. was cool.', [('123 Main Pl.', '')])

    def test_suffix_plz(self):
        self.assertParses('The man at 123 Main Plz. was cool.', [('123 Main Plz.', '')])

    def test_suffix_pt(self):
        self.assertParses('The man at 123 Main Pt. was cool.', [('123 Main Pt.', '')])

    def test_suffix_pts(self):
        self.assertParses('The man at 123 Main Pts. was cool.', [('123 Main Pts.', '')])

    def test_suffix_rd(self):
        self.assertParses('The man at 123 Main Rd. was cool.', [('123 Main Rd.', '')])

    def test_suffix_rte(self):
        self.assertParses('The man at 123 Main Rte. was cool.', [('123 Main Rte.', '')])

    def test_suffix_sq(self):
        self.assertParses('The man at 123 Main Sq. was cool.', [('123 Main Sq.', '')])

    def test_suffix_sqs(self):
        self.assertParses('The man at 123 Main Sqs. was cool.', [('123 Main Sqs.', '')])

    def test_suffix_st(self):
        self.assertParses('The man at 123 Main St. was cool.', [('123 Main St.', '')])

    def test_suffix_sts(self):
        self.assertParses('The man at 123 Main Sts. was cool.', [('123 Main Sts.', '')])

    def test_suffix_ter(self):
        self.assertParses('The man at 123 Main Ter. was cool.', [('123 Main Ter.', '')])

    def test_suffix_terr(self):
        self.assertParses('The man at 123 Main Terr. was cool.', [('123 Main Terr.', '')])

    def test_suffix_trl(self):
        self.assertParses('The man at 123 Main Trl. was cool.', [('123 Main Trl.', '')])

    def test_suffix_wy(self):
        self.assertParses('The man at 123 Main Wy. was cool.', [('123 Main Wy.', '')])

    def test_suffix_unknown_no_period(self):
        # If the suffix is unknown, the period isn't included
        self.assertParses('The man at 123 Main Wacky. was cool.', [('123 Main Wacky', '')])

    def test_postdir_n(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. N.', [('1075 Lake Blvd. N.', '')])

    def test_postdir_s(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. S.', [('1075 Lake Blvd. S.', '')])

    def test_postdir_e(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. E.', [('1075 Lake Blvd. E.', '')])

    def test_postdir_w(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. W.', [('1075 Lake Blvd. W.', '')])

    def test_postdir_nw(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. NW.', [('1075 Lake Blvd. NW.', '')])

    def test_postdir_ne(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. NE.', [('1075 Lake Blvd. NE.', '')])

    def test_postdir_sw(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. SW.', [('1075 Lake Blvd. SW.', '')])

    def test_postdir_se(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. SE.', [('1075 Lake Blvd. SE.', '')])

    def test_postdir_period_nw(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. N.W.', [('1075 Lake Blvd. N.W.', '')])

    def test_postdir_period_ne(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. N.E.', [('1075 Lake Blvd. N.E.', '')])

    def test_postdir_period_sw(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. S.W.', [('1075 Lake Blvd. S.W.', '')])

    def test_postdir_period_se(self):
        self.assertParses('It happened at the garden, 1075 Lake Blvd. S.E.', [('1075 Lake Blvd. S.E.', '')])

    def test_postdir_one_word_street(self):
        self.assertParses('9421 Wabash SW', [('9421 Wabash SW', '')])

    def test_postdir_one_word_street_numbered(self):
        self.assertParses('9421 18th SW', [('9421 18th SW', '')])

    def test_postdir_two_word_street(self):
        self.assertParses('9421 Home Run SW', [('9421 Home Run SW', '')])

    def test_postdir_two_word_street_numbered(self):
        self.assertParses('9421 18th St. SW', [('9421 18th St. SW', '')])

    def test_postdir_central_park_w(self):
        self.assertParses('It happened at 32 West Central Park Avenue W.', [('32 West Central Park Avenue W.', '')])

    def test_postdir_with_in_prefix_washington_dc01(self):
        self.assertParses('It happened on the 600 block of H Street in northeast D.C. and stuff.', [('600 block of H Street northeast', '')])

    def test_postdir_with_in_prefix_washington_dc02(self):
        self.assertParses('It happened on the 600 block of H Street in northeast Washington.', [('600 block of H Street northeast', '')])

    def test_postdir_with_in_prefix_washington_dc03(self):
        self.assertParses('It happened on the 600 block of H Street in NE Washington.', [('600 block of H Street NE', '')])

    def test_postdir_with_in_prefix_washington_dc04(self):
        self.assertParses('It happened on the 600 block of H Street in the NE quadrant', [('600 block of H Street NE', '')])

    def test_postdir_with_in_prefix_washington_dc05(self):
        self.assertParses('It happened on the 600 block of H Street in the NE quadrant', [('600 block of H Street NE', '')])

    def test_postdir_with_in_prefix_washington_dc06(self):
        self.assertParses('It happened on the 600 block of H Street, in northeast D.C. and stuff.', [('600 block of H Street northeast', '')])

    def test_postdir_with_in_prefix_washington_dc07(self):
        self.assertParses('It happened on the 600 block of H Street, in northeast Washington.', [('600 block of H Street northeast', '')])

    def test_postdir_with_in_prefix_washington_dc08(self):
        self.assertParses('It happened on the 600 block of H Street, in NE Washington.', [('600 block of H Street NE', '')])

    def test_postdir_with_in_prefix_washington_dc09(self):
        self.assertParses('It happened on the 600 block of H Street, in the NE quadrant', [('600 block of H Street NE', '')])

    def test_postdir_with_in_prefix_washington_dc10(self):
        self.assertParses('It happened on the 600 block of H Street, in the NE quadrant', [('600 block of H Street NE', '')])

    def test_postdir_with_in_prefix_washington_dc11(self):
        self.assertParses('It happened on the 600 block of H Street, in far northeast Washington.', [('600 block of H Street northeast', '')])

    def test_postdir_seattle(self):
        self.assertParses('Sunday, August 24 at Camp Long, 5200 35th Ave. SW.', [('5200 35th Ave. SW.', '')])

    def test_postdir_comma(self):
        self.assertParses('It happened at 123 Main St., NE, yesterday.', [('123 Main St., NE', '')])

    def test_postdir_not_greedy1(self):
        self.assertParses('at 1620 S. Jackson St. Executive Director Hilary Stern said', [('1620 S. Jackson St.', '')])

    def test_postdir_not_greedy2(self):
        self.assertParses('at 1620 S. Jackson St., Executive Director Hilary Stern said', [('1620 S. Jackson St.', 'Executive Director Hilary Stern')])

    def test_postdir_neighborhood(self):
        self.assertParses('Start at Prezza, 24 Fleet St., North End, 6:30 p.m. $50.', [('Start at Prezza', ''), ('24 Fleet St.', 'North End')])

    def test_one_letter_street(self):
        self.assertParses('It happened at 77 K St.', [('77 K St.', '')])

    def test_one_letter_street_postdir(self):
        self.assertParses('It happened at 77 K St. NE.', [('77 K St. NE.', '')])

    def test_one_letter_street_avenue_x(self):
        self.assertParses('It happened at 1823 Avenue X.', [('1823 Avenue X', '')])

    def test_one_letter_street_avenue_x_abbreviated1(self):
        self.assertParses('It happened at 1823 Ave. X.', [('1823 Ave. X', '')])

    def test_one_letter_street_avenue_x_abbreviated2(self):
        self.assertParses('It happened at 1823 Ave X.', [('1823 Ave X', '')])

    def test_one_letter_street_avenue_x_control(self):
        self.assertParses('It happened at 1823 Main Ave. X marks the spot.', [('1823 Main Ave.', '')])

    def test_one_letter_sanity_check(self):
        self.assertParses('More than 77 ATLASES.', [])

    def test_one_letter_sanity_check2(self):
        self.assertParses('Home prices in 20 U.S. metropolitan areas dropped 15.8 percent in May', [])

    def test_abbreviation_mass(self):
        self.assertParses('It happened at 472 Mass. Ave.', [('472 Mass. Ave.', '')])

class FalsePositives(AddressParsing):
    def test_false_positive_st(self):
        self.assertParses('Copyright 2004-2007 Gothamist', [('2004-2007 Gothamist', '')])

    def test_associated_press(self):
        self.assertParses('Copyright 2008 Associated Press', [])

    def test_university_of_texas1(self):
        self.assertParses('She attends University of Texas at Austin.', [])

    def test_university_of_texas2(self):
        self.assertParses('She attends University Of Texas at Austin.', [])

    def test_university_of_texas3(self):
        self.assertParses('She attends UNIVERSITY OF TEXAS at Austin.', [])

    def test_date1(self):
        self.assertParses('Posted: Friday, 22 May 2009 1:45PM', [])

    def test_date2(self):
        self.assertParses('Posted: Friday, 22 May, 2009 1:45PM', [])

    def test_date3(self):
        self.assertParses('It is scheduled for 22 May 2009.', [])

    def test_date4(self):
        self.assertParses('It is scheduled for 22 October 2009.', [])

class NumberedStreets(AddressParsing):
    def test_block(self):
        self.assertParses('1500 block of 16th Avenue', [('1500 block of 16th Avenue', '')])

    def test_address(self):
        self.assertParses('1500 16th Avenue', [('1500 16th Avenue', '')])

    def test_street_dir1(self):
        self.assertParses('1500 N. 16th Avenue', [('1500 N. 16th Avenue', '')])

    def test_street_number_only(self):
        self.assertParses('327 E. 93 St.', [('327 E. 93 St.', '')])

    def test_suffix_missing1(self):
        self.assertParses('327 E. 93rd', [('327 E. 93rd', '')])

    def test_suffix_missing2(self):
        self.assertParses('327 East 93rd', [('327 East 93rd', '')])

    def test_suffix_missing_plus_period(self):
        self.assertParses('I live at 327 E. 93rd. Where do you live?', [('327 E. 93rd', '')])

    def test_suffix_no_dir(self):
        self.assertParses('327 93rd', [('327 93rd', '')])

    def test_d_suffix(self):
        self.assertParses('327 93d', [('327 93d', '')])

    def test_street_number_only_no_dir(self):
        self.assertParses('327 93 St.', [('327 93 St.', '')])

    def test_street_number_only_suffix_missing(self):
        self.assertParses('327 E. 93', [('327 E', '')]) # TODO: This test passes but is incorrect behavior.

    def test_false_positive1(self):
        self.assertParses('150 61 Year Olds', [('61 Year Olds', '')])

class Intersections(AddressParsing):
    def test_and(self):
        self.assertParses('Near Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_at(self):
        self.assertParses('Near Ashland Ave. at Division St.', [('Ashland Ave. at Division St.', '')])

    def test_prefix_at(self):
        self.assertParses('At Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_prefix_on(self):
        self.assertParses('building on Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_prefix_around(self):
        self.assertParses('Around Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_prefix_corner_of(self):
        self.assertParses('At the corner of Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_area_of(self):
        self.assertParses('In the area of Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_prefix_area_surrounding(self):
        self.assertParses('In the area surrounding Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_prefix_areas_surrounding(self):
        self.assertParses('In the areas surrounding Ashland Ave. and Division St.', [('Ashland Ave. and Division St.', '')])

    def test_prefix_located_on(self):
        self.assertParses('Holy Family Parish located on Roosevelt and May streets', [('Roosevelt and May', '')])

    def test_prefix_vicinity_of(self):
        self.assertParses('Holy Family Parish located at the vicinity of Roosevelt and May streets', [('Roosevelt and May', '')])

    def test_prefix_ran_down(self):
        self.assertParses('The man punched the people as he ran down Washington Street near Dearborn Street, said police.', [('Washington Street near Dearborn Street', '')])

    def test_prefix_running_down(self):
        self.assertParses('The man punched the people while running down Washington Street near Dearborn Street, said police.', [('Washington Street near Dearborn Street', '')])

    def test_to(self):
        self.assertParses('On November 28th, at 10:31pm, officers from District 2 responded to George Street and Langdon Street for a report of a person shot.', [('George Street and Langdon Street', '')])

    def test_that(self):
        self.assertParses('The firm that Microsoft and Apple both tried to buy.', [('Microsoft and Apple', '')])

    def test_directionals1(self):
        self.assertParses('Near N. Ashland Ave. at W. Division St.', [('N. Ashland Ave. at W. Division St.', '')])

    def test_directionals2(self):
        self.assertParses('Near N Ashland Ave. at W Division St.', [('N Ashland Ave. at W Division St.', '')])

    def test_directionals3(self):
        self.assertParses('The el station at N Ashland Ave. at W Division St.', [('N Ashland Ave. at W Division St.', '')])

    def test_address_confusion(self):
        self.assertParses('Around 1200 N. Ashland Ave. at Division St.', [('1200 N. Ashland Ave.', '')])

    def test_intersection1(self):
        self.assertParses('at the intersection of Ashland Ave. and Division St. earlier today', [('Ashland Ave. and Division St.', '')])

    def test_intersection2(self):
        self.assertParses('at the intersection of Ashland Ave. & Division St. earlier today', [('Ashland Ave. & Division St.', '')])

    def test_intersection3(self):
        self.assertParses('at the intersection of Ashland Ave. at Division St. earlier today', [('Ashland Ave. at Division St.', '')])

    def test_intersection4(self):
        self.assertParses('at the intersection of Ashland and Division.', [('Ashland and Division', '')])

    def test_intersection5(self):
        self.assertParses('at the intersection of Ashland near Division.', [('Ashland near Division', '')])

    def test_toward(self):
        self.assertParses('running on Ashland toward Division.', [('Ashland toward Division', '')])

    def test_toward2(self):
        self.assertParses('running on Ashland towards Division.', [('Ashland towards Division', '')])

    def test_north_of(self):
        self.assertParses('on Pulaski Road north of West Lake Street about 3:30 p.m.', [('Pulaski Road north of West Lake Street', '')])

    def test_south_of(self):
        self.assertParses('on Pulaski Road south of West Lake Street about 3:30 p.m.', [('Pulaski Road south of West Lake Street', '')])

    def test_east_of(self):
        self.assertParses('on Pulaski Road east of West Lake Street about 3:30 p.m.', [('Pulaski Road east of West Lake Street', '')])

    def test_west_of(self):
        self.assertParses('on Pulaski Road west of West Lake Street about 3:30 p.m.', [('Pulaski Road west of West Lake Street', '')])

    def test_just_north_of(self):
        self.assertParses('on Pulaski Road just north of West Lake Street about 3:30 p.m.', [('Pulaski Road just north of West Lake Street', '')])

    def test_just_south_of(self):
        self.assertParses('on Pulaski Road just south of West Lake Street about 3:30 p.m.', [('Pulaski Road just south of West Lake Street', '')])

    def test_just_east_of(self):
        self.assertParses('on Pulaski Road just east of West Lake Street about 3:30 p.m.', [('Pulaski Road just east of West Lake Street', '')])

    def test_just_west_of(self):
        self.assertParses('on Pulaski Road just west of West Lake Street about 3:30 p.m.', [('Pulaski Road just west of West Lake Street', '')])

    def test_past(self):
        self.assertParses('on Pulaski Road past West Lake Street about 3:30 p.m.', [('Pulaski Road past West Lake Street', '')])

    def test_just_past(self):
        self.assertParses('on Pulaski Road just past West Lake Street about 3:30 p.m.', [('Pulaski Road just past West Lake Street', '')])

    def test_around(self):
        self.assertParses('on Pulaski Road around West Lake Street about 3:30 p.m.', [('Pulaski Road around West Lake Street', '')])

    def test_crossed(self):
        self.assertParses('as she crossed 122nd Street at Broadway at 3 p.m. while driving', [('122nd Street at Broadway', '')])

    def test_off(self):
        self.assertParses('waiting for a bus on Woodland Road off Eastway Drive late Saturday', [('Woodland Road off Eastway Drive', '')])

    def test_postdir1(self):
        self.assertParses('at Ashland and Division NE', [('Ashland and Division NE', '')])

    def test_postdir2(self):
        self.assertParses('at the corner of 12th St and Maryland Avenue, NE, one block away.', [('12th St and Maryland Avenue, NE', '')])

    def test_postdir3(self):
        self.assertParses('It is Rain City Yoga on Roosevelt and 50th. Earlier this year, the cafe closed.', [('Roosevelt and 50th', '')])

    def test_list_of_intersections(self):
        self.assertParses('The testing will occur in the areas of 18th St & Mission, 22nd St. & Valencia, 23rd St and Folsom, and 18th St and Bryant.', [('18th St & Mission', ''), ('22nd St. & Valencia', ''), ('23rd St and Folsom', ''), ('18th St and Bryant', '')])

    def test_address_multiple_spaces(self):
        self.assertParses('In the area of 18th  St and Mission  Rd', [('18th  St and Mission  Rd', '')])

    def test_one_letter_street_avenue_x(self):
        self.assertParses('At the intersection of Avenue X and Avenue Y.', [('Avenue X and Avenue Y', '')])

    def test_one_letter_street_avenue_x_abbreviated(self):
        self.assertParses('At the intersection of Ave. X and Ave. Y.', [('Ave. X and Ave. Y', '')])

    def test_ignore_intersection_after_between1(self):
        self.assertParses('1060 E 47th St between Ellis and Greenwood Aves', [('1060 E 47th St', '')])

    def test_ignore_intersection_after_between2(self):
        self.assertParses('1060 E 47th St (between Ellis and Greenwood Aves)', [('1060 E 47th St', '')])

    def test_ignore_intersection_after_between_control(self):
        self.assertParses('E 47th St between Ellis and Greenwood Aves', [('E 47th St between Ellis and Greenwood Aves', '')])

class SegmentParsing(AddressParsing):
    def test_basic01(self):
        self.assertParses('Wabash between Adams and Jackson', [('Wabash between Adams and Jackson', '')])

    def test_basic02(self):
        self.assertParses('Wabash from Adams to Jackson', [('Wabash from Adams to Jackson', '')])

    def test_comma01(self):
        self.assertParses('Wabash, between Adams and Jackson', [('Wabash, between Adams and Jackson', '')])

    def test_comma02(self):
        self.assertParses('Wabash, from Adams to Jackson', [('Wabash, from Adams to Jackson', '')])

    def test_comma03(self):
        self.assertParses('Wabash, between Adams, and Jackson', [('Wabash, between Adams, and Jackson', '')])

    def test_comma04(self):
        self.assertParses('Wabash, from Adams, to Jackson', [('Wabash, from Adams, to Jackson', '')])

    def test_withcity01(self):
        self.assertParses('Wabash between Adams and Jackson, Chicago', [('Wabash between Adams and Jackson', 'Chicago')])

    def test_withcity02(self):
        self.assertParses('Wabash between Adams and Jackson in Chicago', [('Wabash between Adams and Jackson', 'Chicago')])

class CityAddressParsing(AddressParsing):
    def test_comma1(self):
        self.assertParses('3000 S. Wabash Ave., Chicago', [('3000 S. Wabash Ave.', 'Chicago')])

    def test_comma2(self):
        self.assertParses('3000 Wabash Ave., Chicago', [('3000 Wabash Ave.', 'Chicago')])

    def test_comma3(self):
        self.assertParses('3000 Wabash Ave.,    Chicago', [('3000 Wabash Ave.', 'Chicago')])

    def test_in1(self):
        self.assertParses('3000 S. Wabash Ave. in Chicago', [('3000 S. Wabash Ave.', 'Chicago')])

    def test_in2(self):
        self.assertParses('3000 Wabash Ave. in Chicago', [('3000 Wabash Ave.', 'Chicago')])

    def test_in_comma1(self):
        self.assertParses('3000 Wabash Ave., in Chicago', [('3000 Wabash Ave.', 'Chicago')])

    def test_in_comma2(self):
        self.assertParses('3000 Wabash Ave.,    in Chicago', [('3000 Wabash Ave.', 'Chicago')])

    def test_multiple(self):
        self.assertParses('3000 Wabash Ave. in Chicago and 123 Main St. in Boston', [('3000 Wabash Ave.', 'Chicago'), ('123 Main St.', 'Boston')])

    def test_intersection1(self):
        self.assertParses('at Adams and Wabash in Chicago', [('Adams and Wabash', 'Chicago')])

    def test_intersection2(self):
        self.assertParses('at Adams and Wabash, Chicago', [('Adams and Wabash', 'Chicago')])

    def test_postdir_comma1(self):
        self.assertParses('3000 Wabash Ave., SW, Chicago', [('3000 Wabash Ave., SW', 'Chicago')])

    def test_postdir_comma2(self):
        self.assertParses('3000 Wabash Ave., SW, in Chicago', [('3000 Wabash Ave., SW', 'Chicago')])

    def test_abbreviation_mass(self):
        self.assertParses('It happened at 472 Mass. Ave. in Cambridge', [('472 Mass. Ave.', 'Cambridge')])

    def test_hyphen(self):
        self.assertParses('Happened at 121 Maple Street, Croton-on-Hudson', [('121 Maple Street', 'Croton-on-Hudson')])

class EdgeCases(AddressParsing):
    def test_uppercase_named_street(self):
        self.assertParses('2826 S. WENTWORTH', [('2826 S. WENTWORTH', '')])

class PhraseTagger(unittest.TestCase):
    def test_double_matching(self):
        # Make sure matching behaves as greedily as possible
        places = ['Lake View', 'Lake View East']
        text = 'In Lake View East today, a Lake View man...'
        tag = phrase_tagger(places)
        self.assertEqual(tag(text), 'In <span>Lake View East</span> today, a <span>Lake View</span> man...')

    def test_empty_phrases(self):
        # Make sure an empty phrase list doesn't result in matching everything
        phrases = []
        text = 'In Lake View East today, a Lake View man...'
        tag = phrase_tagger(phrases)
        self.assertEqual(tag(text), 'In Lake View East today, a Lake View man...')

    def test_matched_phrases_begin(self):
        # Don't try to re-highlight things that have already been highlighted
        phrases = ['South Chicago']
        text = 'on the <addr>South Chicago Ave on the 7400 block</addr>...'
        tag = phrase_tagger(phrases, pre='<addr>', post='</addr>')
        self.assertEqual(tag(text), text)

    def test_matched_phrases_end(self):
        # Don't try to re-highlight things that have already been highlighted
        phrases = ['South Chicago']
        text = 'on the <addr>7400 block of South Chicago</addr>...'
        tag = phrase_tagger(phrases, pre='<addr>', post='</addr>')
        self.assertEqual(tag(text), text)

    def test_matched_phrases_middle(self):
        # Don't try to re-highlight things that have already been highlighted
        phrases = ['South Chicago']
        text = 'on the <addr>7400 block of South Chicago Ave</addr>...'
        tag = phrase_tagger(phrases, pre='<addr>', post='</addr>')
        self.assertEqual(tag(text), text)

if __name__ == "__main__":
    unittest.main()
