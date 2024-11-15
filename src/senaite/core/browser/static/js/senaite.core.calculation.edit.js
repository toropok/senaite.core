window.widgets = window.widgets || {};

document.addEventListener("DOMContentLoaded", () => {
    console.log("Calculation::DOMContentLoaded");
    let DataGrid;
    let testParamTable;
    const getDataGridWidget = () => {
        if (!DataGrid) {
            DataGrid = window.widgets.datagrid;
        }
        return DataGrid;
    }
    const getTestParamTable = () => {
        if (!testParamTable) {
            testParamTable = $("tbody[data-name_prefix='form.widgets.test_parameters']")[0];
        }
        return testParamTable;
    }
    const makeReadonlyTestKeywords = () => {
        $("input[id^='form-widgets-test_parameters-']")
            .filter("[id$='-widgets-keyword']")
            .each((i, e) => $(e).attr("readonly", true));
        $("#form-widgets-test_result").attr("readonly", true);
    }
    const hideAAField = () => {
        $("tbody[data-name_prefix='form.widgets.test_parameters'] > tr")
            .each((i, e) => {
                if (!["AA", "TT"].includes($(e).attr("data-index"))) {
                    $(e).show();
                } else {
                    $(e).hide();
                }
            });
    }

    makeReadonlyTestKeywords();
    hideAAField();
    
    let rawTestInput = document.getElementById("form-widgets-raw_test_keywords");
    let rawTestValue = rawTestInput.value;
    Object.defineProperty(rawTestInput, "value", {
        set(newValue) {
            rawTestValue = newValue;
            const keywords = newValue.split(",").filter(k => k);
            const visibleRows = getDataGridWidget().get_visible_rows(getTestParamTable());
            if (keywords.length === 0) {
                for (let i = 0; i < visibleRows.length - 1; i++) {
                    getDataGridWidget().remove_row(visibleRows[i]);
                }
            } else if (keywords.length > (visibleRows.length - 1)) {
                let newRows = keywords.length - visibleRows.length + 1;
                for (let i = 0; i < newRows; i++) {
                    getDataGridWidget().auto_append_row(getTestParamTable());
                }
            } else if (keywords.length < visibleRows.length - 1) {
                for (let i = 0; i < visibleRows.length - 1; i++) {
                    let row = $(visibleRows[i]).find("input[id$='-widgets-keyword']");
                    if (row) {
                        if (!keywords.includes(row?.val())) {
                            getDataGridWidget().remove_row(visibleRows[i]);
                        }
                    }
                }
            }

            hideAAField();
            getDataGridWidget().trigger_custom_event("update_test_parameters", keywords);
            makeReadonlyTestKeywords();
        },
        get() {
            return rawTestValue;
        }
    });
});