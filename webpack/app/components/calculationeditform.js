import $ from "jquery";

class CalculationEditForm {

    constructor() {
        this.DataGrid = null;
        this.testParamTable = null;
        this.rawTestValue = null;
        this.rawTestInput = document.getElementById("form-widgets-raw_test_keywords");
        if (this.rawTestInput) {
            this.load();
        }
    }

    load() {
        this.rawTestValue = this.rawTestInput.value;
        this.makeReadonlyTestKeywords();
        this.hideAAField();
        this.wrapRawTestInput(this);
    }

    getDataGridWidget() {
        if (!this.DataGrid) {
            this.DataGrid = window.widgets.datagrid;
        }
        return this.DataGrid;
    }

    getTestParamTable() {
        if (!this.testParamTable) {
            this.testParamTable = $("tbody[data-name_prefix='form.widgets.test_parameters']")[0];
        }
        return this.testParamTable;
    }

    makeReadonlyTestKeywords() {
        $("input[id^='form-widgets-test_parameters-']")
            .filter("[id$='-widgets-keyword']")
            .each((i, e) => $(e).attr("readonly", true));
        $("#form-widgets-test_result").attr("readonly", true);
    }

    hideAAField() {
        $("tbody[data-name_prefix='form.widgets.test_parameters'] > tr")
            .each((i, e) => {
                if (!["AA", "TT"].includes($(e).attr("data-index"))) {
                    $(e).show();
                } else {
                    $(e).hide();
                }
            });
    }

    wrapRawTestInput(parent) {
        Object.defineProperty(this.rawTestInput, "value", {
            set: function(newValue) {
                parent.rawTestValue = newValue;
                const keywords = newValue.split(",").filter(k => k);
                const table = parent.getTestParamTable();
                const visibleRows = parent.getDataGridWidget().get_visible_rows(table);
                if (keywords.length === 0) {
                    for (let i = 0; i < visibleRows.length - 1; i++) {
                        parent.getDataGridWidget().remove_row(visibleRows[i]);
                    }
                } else if (keywords.length > (visibleRows.length - 1)) {
                    let newRows = keywords.length - visibleRows.length + 1;
                    for (let i = 0; i < newRows; i++) {
                        parent.getDataGridWidget().auto_append_row(table);
                    }
                } else if (keywords.length < visibleRows.length - 1) {
                    for (let i = 0; i < visibleRows.length - 1; i++) {
                        let row = $(visibleRows[i]).find("input[id$='-widgets-keyword']");
                        if (row) {
                            if (!keywords.includes(row?.val())) {
                                parent.getDataGridWidget().remove_row(visibleRows[i]);
                            }
                        }
                    }
                }

                parent.hideAAField();
                parent.getDataGridWidget().trigger_custom_event("update_test_parameters", keywords);
                parent.makeReadonlyTestKeywords();
            },
            get: function() {
                return parent.rawTestValue;
            }
        });
    }
}

export default CalculationEditForm;
