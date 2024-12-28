# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.CORE.
#
# SENAITE.CORE is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2018-2024 by it's authors.
# Some rights reserved, see README and LICENSE.

import unittest

from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import login
from plone.app.testing import setRoles
from Products.validation import validation as validationService
from senaite.core.content.calculation import ICalculationSchema
from senaite.core.tests.base import DataTestCase
from senaite.core.validators.formula import FormulaValidator
from senaite.core.validators.interimfields import InterimsFieldValidator
from z3c.form.error import MultipleErrors


class Tests(DataTestCase):

    def setUp(self):
        super(Tests, self).setUp()
        setRoles(self.portal, TEST_USER_ID, ['Member', 'LabManager'])
        login(self.portal, TEST_USER_NAME)

    def test_UniqueFieldValidator(self):
        login(self.portal, TEST_USER_NAME)

        clients = self.portal.clients
        client1 = clients['client-2']  # not Happy Hills
        self.assertEqual(
            client1.schema.get('ClientID').validate('HH', client1),
            u"Validation failed: 'HH' is not unique")
        self.assertEqual(
            None,
            client1.schema.get(
                'title').validate(
                    'Another Client',
                    client1))

    def test_ServiceKeywordValidator(self):
        login(self.portal, TEST_USER_NAME)

        services = self.portal.bika_setup.bika_analysisservices
        service1 = services['analysisservice-1']

        self.assertEqual(
            service1.schema.get('Keyword').validate('', service1),
            u'Analysis Keyword is required, please correct.')
        self.assertEqual(
            service1.schema.get('Keyword').validate('&', service1),
            u'Validation failed: keyword contains invalid characters')
        self.assertEqual(
            service1.schema.get('Keyword').validate('Ca', service1),
            u"Validation failed: keyword is already in use")
        self.assertEqual(
            service1.schema.get('Keyword').validate('TV', service1),
            u"Validation failed: keyword is already in use by calculation 'Titration'")
        self.assertEqual(
            None,
            service1.schema.get(
                'Keyword').validate(
                    'VALID_KW',
                    service1))

    def test_InterimFieldsValidator(self):
        login(self.portal, TEST_USER_NAME)

        calcs = self.portal.setup.calculations
        # Titration
        calc1 = calcs['calculation-1']

        key = calc1.id + 'interims'

        interim_fields = []
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        self.assertIsNone(
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields))

        interim_fields = [{'keyword': '&',
                           'title': 'Titration Volume',
                           'unit': '',
                           'default': ''},
                          ]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False

        with self.assertRaises(MultipleErrors) as arc:
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields)
        self.assertEqual(
            str(arc.exception.errors[0][2]), "'keyword' contains invalid characters")

        interim_fields = [
            {'keyword': 'XXX',
             'title': 'Gross Mass',
             'unit': '',
             'default': ''},
            {'keyword': 'TV', 'title': 'Titration Volume', 'unit': '', 'default': ''}]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        with self.assertRaises(MultipleErrors) as arc:
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields)
        self.assertEqual(str(
            arc.exception.errors[0][2]), "column title 'Gross Mass' must have keyword 'GM'")

        interim_fields = [
            {'keyword': 'GM', 'title': 'XXX', 'unit': '', 'default': ''},
            {'keyword': 'TV', 'title': 'Titration Volume', 'unit': '', 'default': ''}]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        with self.assertRaises(MultipleErrors) as arc:
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields)
        self.assertEqual(str(
            arc.exception.errors[0][2]), "keyword 'GM' must have column title 'Gross Mass'")

        interim_fields = [
            {'keyword': 'TV',
             'title': 'Titration Volume',
             'unit': '',
             'default': ''},
            {'keyword': 'TV', 'title': 'Titration Volume 1', 'unit': '', 'default': ''}]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        with self.assertRaises(MultipleErrors) as arc:
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields)
        self.assertEqual(
            str(arc.exception.errors[0][2]), "'keyword' duplicates found")

        interim_fields = [
            {'keyword': 'TV',
             'title': 'Titration Volume',
             'unit': '',
             'default': ''},
            {'keyword': 'TF', 'title': 'Titration Volume', 'unit': '', 'default': ''}]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        with self.assertRaises(MultipleErrors) as arc:
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields)
        self.assertEqual(
            str(arc.exception.errors[0][2]), "'title' duplicates found")

        interim_fields = [
            {'keyword': 'TV',
             'title': 'Titration Volume',
             'unit': '',
             'default': ''},
            {'keyword': 'TF', 'title': 'Titration Factor', 'unit': '', 'default': ''}]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST['validated'] = None
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        with self.assertRaises(MultipleErrors) as arc:
            InterimsFieldValidator(
                calc1, self.portal.REQUEST, None, None, None
            ).validate(interim_fields)
        self.assertEqual(
            str(arc.exception.errors[0][2]), "keyword 'TV' must have column title 'Titr Vol'")

    def test_UncertaintyValidator(self):
        login(self.portal, TEST_USER_NAME)
        services = self.portal.bika_setup.bika_analysisservices
        serv1 = services['analysisservice-1']
        v = validationService.validatorFor('uncertainties_validator')
        field = serv1.schema['Uncertainties']
        key = serv1.id + field.getName()

        uncertainties = [{'intercept_min': '100.01',
                          'intercept_max': '200', 'errorvalue': '200%'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Error percentage must be between 0 and 100")

        uncertainties = [{'intercept_min': 'a',
                          'intercept_max': '200', 'errorvalue': '10%'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Min values must be numeric")

        uncertainties = [{'intercept_min': '100.01',
                          'intercept_max': 'a', 'errorvalue': '10%'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Max values must be numeric")

        uncertainties = [{'intercept_min': '100.01',
                          'intercept_max': '200', 'errorvalue': 'a%'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Error values must be numeric")

        uncertainties = [{'intercept_min': '200',
                          'intercept_max': '100', 'errorvalue': '10%'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Max values must be greater than Min values")

        uncertainties = [{'intercept_min': '100',
                          'intercept_max': '200', 'errorvalue': '-5%'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Error percentage must be between 0 and 100")

        uncertainties = [{'intercept_min': '100',
                          'intercept_max': '200', 'errorvalue': '-5'}]
        self.portal.REQUEST['Uncertainties'] = uncertainties
        if key in self.portal.REQUEST:
            self.portal.REQUEST[key] = False
        res = v(uncertainties, instance=serv1,
                field=field, REQUEST=self.portal.REQUEST)
        self.failUnlessEqual(
            res, "Validation failed: Error value must be 0 or greater")

    def test_FormulaValidator(self):
        login(self.portal, TEST_USER_NAME)

        calcs = self.portal.setup.calculations
        calc1 = calcs['calculation-1']

        interim_fields = [
            {'keyword': 'TV',
             'title': 'Titration Volume',
             'unit': '',
             'default': ''},
            {'keyword': 'TF', 'title': 'Titration Factor', 'unit': '', 'default': ''}]
        self.portal.REQUEST.form['interims'] = interim_fields
        self.portal.REQUEST.form['formula'] = "[TV] * [TF] * [Wrong]"
        self.assertEqual(
            FormulaValidator(
                calc1,
                self.portal.REQUEST,
                None,
                ICalculationSchema,
                None).validate(self.portal.REQUEST.form)[0].message,
            "AnalysesServices not found for keywords: Wrong")

        self.portal.REQUEST.form['formula'] = "[TV] * [TF]"
        self.assertEqual(
            tuple(),
            FormulaValidator(
                calc1,
                self.portal.REQUEST,
                None,
                ICalculationSchema,
                None).validate(self.portal.REQUEST.form))


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(Tests))
    return suite
