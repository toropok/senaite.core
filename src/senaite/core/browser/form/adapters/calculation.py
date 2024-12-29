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

import re

from bika.lims import api
from bika.lims.api.analysisservice import get_by_keyword
from senaite.core.browser.form.adapters import EditFormAdapterBase
from senaite.core.content.calculation import calculate_formula
from senaite.core.content.calculation import ICalculationSchema
from senaite.core.validators.formula import FormulaValidator

FORMULA_RX = re.compile(r"\[[^\]]*\]")
INTERIM_KEYWORD_RX = re.compile(r"interim_fields\.(\d+)\.widgets\.keyword$")
IMPORT_MODULES_RX = re.compile(r"imports\.(\d+)\.widgets\.module$")
TEST_KEYWORDS_RX = re.compile(r"test_parameters\.(\d+)\.widgets\.keyword$")
TEST_VALUE_RX = re.compile(r"test_parameters\.(\d+)\.widgets\.value$")

FIELD_DEPENDENT_SERVICES = "form.widgets.dependent_services"
FIELD_FORMULA = "form.widgets.formula"
FIELD_IMPORTS_FUNC = "form.widgets.imports.{}.widgets.function"
FIELD_INTERIM_VALUE = "form.widgets.interim_fields.{}.widgets.value"
FIELD_TEST_RESULT = "form.widgets.test_result"
FIELD_TEST_KEYWORD = "form.widgets.test_parameters.{}.widgets.keyword"
FIELD_TEST_VALUE = "form.widgets.test_parameters.{}.widgets.value"


class EditForm(EditFormAdapterBase):
    """Edit form adapter for Calculation
    """

    def initialized(self, data):
        self.add_callback("body",
                          "update_test_parameters",
                          "update_test_parameters")
        self.add_callback("body",
                          "datagrid:row_added",
                          "update_form")
        self.add_callback("body",
                          "datagrid:row_removed",
                          "update_form")
        return self.data

    def modified(self, data):
        errors = self.validate_formula(data)
        if errors:
            err_msg = "; ".join([err.message for err in errors])
            self.add_error_field(FIELD_FORMULA, err_msg)
            return self.data

        # clean prev error messages if validation passed
        self.add_error_field(FIELD_FORMULA, "")
        return self.update_form(data)

    def callback(self, data):
        name = data.get("name")
        if not name:
            return
        method = getattr(self, name, None)
        if not callable(method):
            return
        return method(data)

    def update_form(self, data):
        keywords = self.process_keywords(data)
        self.add_update_field("form.widgets.raw_test_keywords",
                              ",".join(keywords.keys()))
        return self.data

    def process_keywords(self, data):
        interim_keywords = self.get_interimfields_keywords(data)
        formula_keywords = self.process_formula(data, interim_keywords)
        test_keywords = self.get_test_keywords(data)

        dep_services_uids = map(
            api.get_uid,
            get_by_keyword(
                [k for k in formula_keywords if k not in interim_keywords]))
        self.add_update_field(FIELD_DEPENDENT_SERVICES, dep_services_uids)

        return self.update_keywords_value(formula_keywords, test_keywords)

    def update_keywords_value(self, formula_keywords, test_keywords):
        for kw in formula_keywords.keys():
            if kw in test_keywords.keys():
                formula_keywords[kw] = test_keywords.get(kw)
        return formula_keywords

    def update_test_parameters(self, data):
        keywords = self.process_keywords(data)
        items = keywords.items()
        kws = []
        for index, item in enumerate(items):
            kws.append(item[0])
            self.add_update_field(FIELD_TEST_KEYWORD.format(index), item[0])
            self.add_update_field(FIELD_TEST_VALUE.format(index), item[1])
        imports = self.get_imports(data)
        self.calculate_result(data, parameters=keywords, imports=imports)
        return self.data

    def process_formula(self, data, interim_keywords):
        form = data.get("form")
        formula = form.get(FIELD_FORMULA) or ""
        formula_keywords = self.parse_formula(formula)
        result_keywords = {kw: interim_keywords.get(
            kw, "") for kw in formula_keywords}
        return result_keywords

    def get_interimfields_keywords(self, data):
        form = data.get("form")
        keywords = {}
        for k, v in form.items():
            interim_match = INTERIM_KEYWORD_RX.search(k)
            if interim_match:
                idx = interim_match.group(1)
                value = form.get(FIELD_INTERIM_VALUE.format(idx))
                keywords.update({v: value})
        return keywords

    def parse_formula(self, formula):
        keywords = FORMULA_RX.findall(formula)
        return set(map(lambda kw: re.sub(r"[\[\]]", "", kw), keywords))

    def get_test_keywords(self, data):
        form = data.get("form")
        keywords = {}
        for k, v in form.items():
            test_match = TEST_KEYWORDS_RX.search(k)
            if test_match:
                idx = test_match.group(1)
                value = form.get(FIELD_TEST_VALUE.format(idx))
                keywords.update({v: value})
        return keywords

    def get_imports(self, data):
        form = data.get("form")
        imports = []
        for k, v in form.items():
            module_match = IMPORT_MODULES_RX.search(k)
            if module_match:
                idx = module_match.group(1)
                imports.append({
                    "module": v,
                    "function": form.get(FIELD_IMPORTS_FUNC.format(idx)),
                })
        return imports

    def get_count_test_rows(self, data):
        form = data.get("form")
        positions = [k for k in form.keys() if TEST_KEYWORDS_RX.search(k)]
        return len(positions)

    def get_interim_fields(self, data):
        return [{"keyword": i} for i in self.get_interimfields_keywords(data)]

    def validate_formula(self, data):
        form = data.get("form")
        formula = form.get(FIELD_FORMULA) or ""
        ifields = self.get_interim_fields(data)
        validator = FormulaValidator(
            self.context, self.request, None, ICalculationSchema, None)
        return validator.validate({"formula": formula,
                                   "interim_fields": ifields})

    def calculate_result(self, data, parameters=None, imports=None):
        form = data.get("form")
        formula = " ".join(form.get(FIELD_FORMULA, "").splitlines())
        if parameters is None:
            parameters = self.get_test_keywords(data)
        if imports is None:
            imports = self.get_imports(data)
        result = calculate_formula(formula, parameters, imports)
        self.add_update_field(FIELD_TEST_RESULT, result)
        return self.data
