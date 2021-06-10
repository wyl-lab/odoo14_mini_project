import DocElement from './DocElement';

/**
 * Qrcode doc element. Currently only Code-128 is supported.
 * @class
 */
export default class QrCodeElement extends DocElement {
    constructor(id, initialData, rb) {
        super(rb.getLabel('docElementImage'), id, 80, 80, rb);
        this.elQrCode = null;
        this.content = '';
        this.format = 'QR';
        this.displayValue = false;
        this.spreadsheet_hide = false;
        this.spreadsheet_column = '';
        this.spreadsheet_colspan = '';
        this.spreadsheet_addEmptyRow = false;
        this.setInitialData(initialData);
        this.name = this.rb.getLabel('docElementQrCode');
        $(`#rbro_menu_item_name${this.id}`).text(this.name);
    }

    setup(openPanelItem) {
        super.setup(openPanelItem);
        this.createElement();
        if (this.content !== '') {
            this.updateQrCode();
        }
        this.updateDisplay();
        this.updateStyle();
    }

    setValue(field, value, elSelector, isShown) {
        super.setValue(field, value, elSelector, isShown);
        if (field === 'content' ||field === 'format' || field === 'displayValue' || field === 'height') {
            this.updateQrCode();
            this.updateDisplay();
        }
    }

    /**
     * Returns all data fields of this object. The fields are used when serializing the object.
     * @returns {String[]}
     */
    getFields() {
        return ['id', 'containerId', 'x', 'y', 'height', 'content', 'format', 'displayValue',
            'printIf', 'removeEmptyElement',
            'spreadsheet_hide', 'spreadsheet_column', 'spreadsheet_colspan', 'spreadsheet_addEmptyRow'];
    }

    getElementType() {
        return DocElement.type.qrCode;
    }

    updateDisplayInternal(x, y, width, height) {
        if (this.el !== null) {
            let props = { left: this.rb.toPixel(x), top: this.rb.toPixel(y),
                width: this.rb.toPixel(width), height: this.rb.toPixel(height) };
            this.el.css(props);
        }
    }

    /**
     * Returns allowed sizers when element is selected.
     * @returns {String[]}
     */
    getSizers() {
        return ['N', 'S'];
    }

    getXTagId() {
        return 'rbro_qr_code_element_position_x';
    }

    getYTagId() {
        return 'rbro_qr_code_element_position_y';
    }

    getHeightTagId() {
        return 'rbro_qr_code_element_height';
    }

    createElement() {
        this.el = $(`<div id="rbro_el${this.id}" class="rbroDocElement rbroQrCodeElement"></div>`);
        this.elQrCode = $('<div></div>');
        this.el.append(this.elQrCode);
        this.appendToContainer();
        this.updateQrCode();
        super.registerEventHandlers();
    }

    remove() {
        super.remove();
    }

    updateQrCode() {
        this.elQrCode.empty();
        let valid = false;
        let options = {text: '', width: this.displayValue ? (this.heightVal - 22) : this.heightVal,
            height: this.displayValue ? (this.heightVal - 22) : this.heightVal,};
        if (this.content !== '' && this.content.indexOf('${') === -1) {
            try {
                options['text'] = this.content;
                this.elQrCode.qrcode(options);
                valid = true;
            } catch (ex) {
            }
        }
        if (!valid) {
            // in case qrcode cannot be created because of invalid input use default content appropriate
            // for selected format
            if (this.format === 'QR') {
                options['text'] = '12345678';
            }
            this.elQrCode.qrcode(options);
            
        }
        
        this.elQrCode.width(this.displayValue ? (this.heightVal - 22) : this.heightVal);
        this.elQrCode.height(this.displayValue ? (this.heightVal - 22) : this.heightVal);

        this.widthVal = this.elQrCode.width();
        this.width = '' + this.widthVal;
        this.heightVal = this.elQrCode.height();
        this.height = '' + this.heightVal;
    }

    /**
     * Adds SetValue commands to command group parameter in case the specified parameter is used in any of
     * the object fields.
     * @param {Parameter} parameter - parameter which will be renamed.
     * @param {String} newParameterName - new name of the parameter.
     * @param {CommandGroupCmd} cmdGroup - possible SetValue commands will be added to this command group.
     */
    addCommandsForChangedParameterName(parameter, newParameterName, cmdGroup) {
        this.addCommandForChangedParameterName(parameter, newParameterName, 'rbro_qr_code_element_content', 'content', cmdGroup);
        this.addCommandForChangedParameterName(parameter, newParameterName, 'rbro_qr_code_element_print_if', 'printIf', cmdGroup);
    }
}
