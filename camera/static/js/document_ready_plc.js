var plc_get_selected_reg_url = $('#plc-get-selected-reg-url').data('url');
var plc_setM_url = $('#plc-setM-url').data('url');
var plc_getM_url = $('#plc-getM-url').data('url');
var plc_writeD_url = $('#plc-writeD-url').data('url');
var plc_readD_url = $('#plc-readD-url').data('url');
const M202 = $('input[name="M202"]');
const M1 = $('input[name="M1"]');
const M11 = $('input[name="M11"]');
const M212 = $('input[name="M212"]');
const M4 = $('input[name="M4"]');
const M14 = $('input[name="M14"]');
const D850 = $('#D850');
const D864 = $('#D864');
const D856 = $('#D856');
const D870 = $('#D870');
const D814 = $('#D814');

function get_selected_reg() {
    $.ajax({
        url: plc_get_selected_reg_url,
        type: 'POST',
        beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function(data) {
            console.log(data.reg_values);
            for (let key in data.reg_values) {
                if (data.reg_values.hasOwnProperty(key)) {
                    console.log(key);
                    if (key[0] == "M") {
                        const id = '#' + key + '-' + data.reg_values[key];
                        $(id).prop('checked', true);
                    } else {
                        const id = '#' + key;
                        console.log(id);
                        $(id).val(data.reg_values[key]);
                    }
                }
            }
        }
    });
}

function plc_setM(reg, value) {
    $.ajax({
        url: plc_setM_url,
        type: "POST",
        data: {
            "register": reg,
            "value": value
        },
        beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function(data) {
            console.log(data);
        }
    });
}

function plc_writeD(reg) {
    const value = $('#' + reg).val();
    $.ajax({
        url: plc_writeD_url,
        type: "POST",
        data: {
            "register": reg,
            "value": value
        },
        beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function(data) {
            console.log(data);
            $('#' + reg).val(data.value);
        }
    });
}

function plc_getM(reg) {
    $.ajax({
        url: plc_getM_url,
        type: "POST",
        data: {
            "register": reg
        },
        beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function(data) {
            console.log(data);
            if (data.value == "1") {
                $('#' + reg + "-1").prop('checked', true);
            } else {
                $('#' + reg + "-0").prop('checked', true);
            }
        }
    });
}

function plc_readD(reg) {
    $.ajax({
        url: plc_readD_url,
        type: "POST",
        data: {
            "register": reg
        },
        beforeSend: function(xhr) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        },
        success: function(data) {
            console.log(data);
            $('#' + reg).val(data.value);
        }
    });
}

// 定义执行寄存器操作的函数
function performRegAction(buttonId) {
    console.log(buttonId);
    if (buttonId[0] == "M") {
        let [reg, btn, action] = buttonId.split("-");
        if (action == "r") {
            plc_getM(reg);
        } else {
            if ($("#" + reg + "-1").is(":checked")) {
                plc_setM(reg, "1");
            } else {
                plc_setM(reg, "0");
            }
        }
    } else {
        // D reg
        let [reg, action] = buttonId.split("-");
        if (action == 'r') {
            plc_readD(reg);
        } else {
            plc_writeD(reg);
        }
    }
}

$(document).ready(function () {
    get_selected_reg();

    $('.reg-btn').on('click', function () {
        // 获取点击按钮的数据属性
        const buttonId = $(this).attr('id');

        // 根据获取的属性执行相应的操作
        performRegAction(buttonId);
    });

});

