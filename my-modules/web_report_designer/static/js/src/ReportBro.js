import Document from './Document';
import PopupWindow from './PopupWindow';
import AddDeleteDocElementCmd from './commands/AddDeleteDocElementCmd';
import AddDeleteParameterCmd from './commands/AddDeleteParameterCmd';
import AddDeleteStyleCmd from './commands/AddDeleteStyleCmd';
import Command from './commands/Command';
import CommandGroupCmd from './commands/CommandGroupCmd';
import SetValueCmd from './commands/SetValueCmd';
import Band from './container/Band';
import Container from './container/Container';
import DocumentProperties from './data/DocumentProperties';
import Parameter from './data/Parameter';
import Style from './data/Style';
import DocElement from './elements/DocElement';
import FrameElement from './elements/FrameElement';
import PageBreakElement from './elements/PageBreakElement';
import SectionElement from './elements/SectionElement';
import TableElement from './elements/TableElement';
import TableTextElement from './elements/TableTextElement';
import locales from './i18n/locales';
import BarCodeElementPanel from './panels/BarCodeElementPanel';
import QrCodeElementPanel from './panels/QrCodeElementPanel';
import DocumentPropertiesPanel from './panels/DocumentPropertiesPanel';
import EmptyDetailPanel from './panels/EmptyDetailPanel';
import FrameElementPanel from './panels/FrameElementPanel';
import ImageElementPanel from './panels/ImageElementPanel';
import LineElementPanel from './panels/LineElementPanel';
import SectionBandElementPanel from './panels/SectionBandElementPanel';
import SectionElementPanel from './panels/SectionElementPanel';
import MainPanel from './menu/MainPanel';
import MainPanelItem from './menu/MainPanelItem';
import MenuPanel from './menu/MenuPanel';
import PageBreakElementPanel from './panels/PageBreakElementPanel';
import ParameterPanel from './panels/ParameterPanel';
import StylePanel from './panels/StylePanel';
import TableElementPanel from './panels/TableElementPanel';
import TableBandElementPanel from './panels/TableBandElementPanel';
import TextElementPanel from './panels/TextElementPanel';
import * as utils from './utils';

/**
 * Used for the main ReportBro instance.
 * @class
 */
export default class ReportBro {
    constructor(element, properties) {
        this.element = element;
        this.nextId = 1;
        this.locale = locales[properties.localeKey || 'zh_cn'];

        this.properties = {
            additionalFonts: [],
            adminMode: true,
            cmdExecutedCallback: null,
            enableSpreadsheet: true,
            // fonts: [
            //     { name: 'Courier', value: 'courier' },
            //     { name: 'Helvetica', value: 'helvetica' },
            //     { name: 'Times New Roman', value: 'times' }
            // ],
            fonts: [{ name: 'yahei', value: 'Microsoft YaHei' }],
            localStorageReportKey: null,
            menuShowButtonLabels: false,
            menuShowDebug: false,
            menuSidebar: false,
            saveCallback: null,
            showGrid: true,
            patternAdditionalDates: [],
            patternAdditionalNumbers: [],
            patternCurrencySymbol: '$',
            patternDates: [
                { name: 'yyyy/M/d', description: this.locale['patternDate1'] }, 
                { name: 'yyyy/M/d hh:mm', description: this.locale['patternDate2'] }, 
                { name: 'yyyy/MMM/d', description: this.locale['patternDate3'] }, 
                { name: 'yyyy/MM/dd', description: this.locale['patternDate4'] }
            ],
            patternLocale: 'en',
            patternNumbers: [
                { name: '#,##0', description: this.locale['patternNumber1'] },
                { name: '0.000', description: this.locale['patternNumber2'] },
                { name: '0.00##', description: this.locale['patternNumber3'] },
                { name: '#,##0.00', description: this.locale['patternNumber4'] },
                { name: '$ #,##0.00', description: this.locale['patternNumber5'] }
            ],
            reportServerTimeout: 20000,
            reportServerUrl: '/report/get',//https://www.reportbro.com/report/run
            reportServerUrlCrossDomain: false
        };
        if (properties) {
            for (let prop in properties) {
                if (this.properties.hasOwnProperty(prop)) {
                    this.properties[prop] = properties[prop];
                }
            }
            $.extend( this.locale, properties['locale'] || {} );
        }
        if (this.properties.additionalFonts.length > 0) {
            this.properties.fonts = this.properties.fonts.concat(this.properties.additionalFonts);
        }
        if (this.properties.patternAdditionalDates.length > 0) {
            this.properties.patternDates = this.properties.patternDates.concat(this.properties.patternAdditionalDates);
        }
        if (this.properties.patternAdditionalNumbers.length > 0) {
            this.properties.patternNumbers = this.properties.patternNumbers.concat(this.properties.patternAdditionalNumbers);
        }

        this.detailData = null;
        this.document = new Document(element, this.properties.showGrid, this);
        this.popupWindow = new PopupWindow(element, this);
        this.docElements = [];
        this.headerBand = new Band(Band.bandType.header, false, '', '', this);
        this.contentBand = new Band(Band.bandType.content, false, '', '', this);
        this.footerBand = new Band(Band.bandType.footer, false, '', '', this);
        this.parameterContainer = new Container('0_parameters', this.getLabel('parameters'), this);
        this.styleContainer = new Container('0_styles', this.getLabel('styles'), this);
        this.documentProperties = new DocumentProperties(this);
        this.clipboardElements = [];

        this.mainPanel = new MainPanel(element, this.headerBand, this.contentBand, this.footerBand,
                this.parameterContainer, this.styleContainer, this);
        this.menuPanel = new MenuPanel(element, this);
        this.activeDetailPanel = 'none';
        this.detailPanels = {
            'none': new EmptyDetailPanel(element, this),
            'bar_code': new BarCodeElementPanel(element, this),
            'qr_code': new QrCodeElementPanel(element, this),
            'frame': new FrameElementPanel(element, this),
            'text': new TextElementPanel(element, this),
            'line': new LineElementPanel(element, this),
            'image': new ImageElementPanel(element, this),
            'page_break': new PageBreakElementPanel(element, this),
            'table': new TableElementPanel(element, this),
            'table_band': new TableBandElementPanel(element, this),
            'parameter': new ParameterPanel(element, this),
            'section': new SectionElementPanel(element, this),
            'section_band': new SectionBandElementPanel(element, this),
            'style': new StylePanel(element, this),
            'documentProperties': new DocumentPropertiesPanel(this.documentProperties, element, this)
        };

        this.commandStack = [];
        this.lastCommandIndex = -1;
        this.modified = false;
        this.selectionSinceLastCommand = false;
        this.objectMap = {};
        this.containers = [this.headerBand, this.contentBand, this.footerBand];
        this.selections = [];
        this.reportKey = null;  // key of last report preview to allow download of xlsx file for this report

        this.browserDragType = '';
        this.browserDragId = '';

        this.documentProperties.setPanelItem(this.mainPanel.getDocumentPropertiesItem());
        this.initObjectMap();

        $(document).keydown(event => {
            // check metaKey instead of ctrl for Mac
            if (event.metaKey || event.ctrlKey) {
                switch (event.which) {
                    case 67: {
                        // Ctrl + C: copy
                        if (!(event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement)) {
                            let cleared = false;
                            let idMap = {};
                            let serializedObj;
                            let i;
                            for (let selectionId of this.selections) {
                                let obj = this.getDataObject(selectionId);
                                if ((obj instanceof DocElement && !(obj instanceof TableTextElement)) ||
                                        (obj instanceof Parameter && !obj.showOnlyNameType) ||
                                        (obj instanceof Style)) {
                                    if (!cleared) {
                                        this.clipboardElements = [];
                                        cleared = true;
                                    }
                                    if (!(obj.getId() in idMap)) {
                                        idMap[obj.getId()] = true;
                                        serializedObj = obj.toJS();
                                        this.clipboardElements.push(serializedObj);
                                        if (obj instanceof DocElement) {
                                            serializedObj.baseClass = 'DocElement';
                                            if (obj instanceof FrameElement) {
                                                let nestedElements = [];
                                                obj.appendContainerChildren(nestedElements);
                                                for (let nestedElement of nestedElements) {
                                                    if (nestedElement.getId() in idMap) {
                                                        // in case a nested element is also selected we make sure to add it only once to
                                                        // the clipboard objects and to add it after its parent element
                                                        for (i = 0; i < this.clipboardElements.length; i++) {
                                                            if (nestedElement.getId() === this.clipboardElements[i].id) {
                                                                this.clipboardElements.splice(i, 1);
                                                                break;
                                                            }
                                                        }
                                                    } else {
                                                        idMap[nestedElement.getId()] = true;
                                                    }
                                                    serializedObj = nestedElement.toJS();
                                                    serializedObj.baseClass = 'DocElement';
                                                    this.clipboardElements.push(serializedObj);
                                                }
                                            }
                                        } else if (obj instanceof Parameter) {
                                            serializedObj.baseClass = 'Parameter';
                                        } else if (obj instanceof Style) {
                                            serializedObj.baseClass = 'Style';
                                        }
                                    }
                                }
                            }
                            event.preventDefault();
                        }
                        break;
                    }
                    case 86: {
                        // Ctrl + V: paste
                        if (!(event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement)) {
                            let cmd;
                            let cmdGroup = new CommandGroupCmd('Paste from clipboard', this);
                            let mappedContainerIds = {};
                            for (let clipboardElement of this.clipboardElements) {
                                clipboardElement.id = this.getUniqueId();
                                if (clipboardElement.baseClass === 'DocElement') {
                                    if (clipboardElement.linkedContainerId) {
                                        let linkedContainerId = this.getUniqueId();
                                        mappedContainerIds[clipboardElement.linkedContainerId] = linkedContainerId;
                                        clipboardElement.linkedContainerId = linkedContainerId;
                                    }
                                    if (clipboardElement.elementType === DocElement.type.table) {
                                        TableElement.removeIds(clipboardElement);
                                    }
                                }
                            }
                            for (let clipboardElement of this.clipboardElements) {
                                if (clipboardElement.baseClass === 'DocElement') {
                                    // map id of container in case element is inside other pasted container (frame/band)
                                    if (clipboardElement.containerId in mappedContainerIds) {
                                        clipboardElement.containerId = mappedContainerIds[clipboardElement.containerId];
                                        // since element is inside pasted container we can keep x/y coordinates
                                    } else {
                                        let pasteToY = 0;
                                        let container = this.getDataObject(clipboardElement.containerId);
                                        if (container !== null) {
                                            // determine new y-coord so pasted element is in
                                            // visible area of scrollable document
                                            let containerOffset = container.getOffset();
                                            let containerSize = container.getContentSize();
                                            let contentScrollY = this.getDocument().getContentScrollPosY();
                                            if (contentScrollY > containerOffset.y &&
                                                (contentScrollY + clipboardElement.height) < (containerOffset.y + containerSize.height)) {
                                                pasteToY = contentScrollY - containerOffset.y;
                                            }
                                        }
                                        clipboardElement.x = 0;
                                        clipboardElement.y = pasteToY;
                                    }
                                    cmd = new AddDeleteDocElementCmd(
                                        true, clipboardElement.elementType, clipboardElement,
                                        clipboardElement.id, clipboardElement.containerId, -1, this);
                                    cmdGroup.addCommand(cmd);

                                } else if (clipboardElement.baseClass === 'Parameter') {
                                    Parameter.removeIds(clipboardElement);
                                    cmd = new AddDeleteParameterCmd(
                                        true, clipboardElement, clipboardElement.id,
                                        this.parameterContainer.getId(), -1, this);
                                    cmdGroup.addCommand(cmd);
                                } else if (clipboardElement.baseClass === 'Style') {
                                    cmd = new AddDeleteStyleCmd(
                                        true, clipboardElement, clipboardElement.id,
                                        this.styleContainer.getId(), -1, this);
                                    cmdGroup.addCommand(cmd);
                                }
                            }
                            if (!cmdGroup.isEmpty()) {
                                this.executeCommand(cmdGroup);
                                let clearSelection = true;
                                for (let clipboardElement of this.clipboardElements) {
                                    this.selectObject(clipboardElement.id, clearSelection);
                                    clearSelection = false;
                                }
                            }
                            event.preventDefault();
                        }
                        break;
                    }
                    case 89: {
                        // Ctrl + Y: redo
                        this.redoCommand();
                        event.preventDefault();
                        break; 
                    }
                    case 90: {
                        // Ctrl + Z: undo
                        this.undoCommand();
                        event.preventDefault();
                        break;
                    }
                }
            } else {
                if (event.which === 27) {  // escape
                    this.popupWindow.hide();
                }
                else if (!(event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement)) {
                    switch (event.which) {
                        case 8:  // backspace
                        case 46: {  // delete
                            let cmdGroup = new CommandGroupCmd('Delete', this);
                            for (let selectionId of this.selections) {
                                let obj = this.getDataObject(selectionId);
                                if (obj instanceof DocElement) {
                                    obj.addCommandsForDelete(cmdGroup);
                                }
                            }
                            if (!cmdGroup.isEmpty()) {
                                this.executeCommand(cmdGroup);
                            }
                            event.preventDefault();
                            break;
                        }
                        case 37:  // left
                        case 38:  // up
                        case 39:  // right
                        case 40: {  // down
                            let cmdGroup = new CommandGroupCmd('Move element', this);
                            let tagId;
                            let field = (event.which === 37 || event.which === 39) ? 'x' : 'y';
                            let bandWidth = this.getDocumentProperties().getContentSize().width;
                            for (let selectionId of this.selections) {
                                let obj = this.getDataObject(selectionId);
                                if (obj instanceof DocElement) {
                                    if (event.which === 37 || event.which === 39) {
                                        tagId = obj.getXTagId();
                                    } else {
                                        tagId = obj.getYTagId();
                                    }
                                    if (tagId !== '') {
                                        let val = null;
                                        if (event.which === 37) {
                                            if (obj.getValue('xVal') > 0) {
                                                val = obj.getValue('xVal') - 1;
                                            }
                                        } else if (event.which === 38) {
                                            if (obj.getValue('yVal') > 0) {
                                                val = obj.getValue('yVal') - 1;
                                            }
                                        } else if (event.which === 39) {
                                            let containerSize = obj.getContainerContentSize();
                                            if ((obj.getValue('xVal') + obj.getValue('widthVal')) < containerSize.width) {
                                                val = obj.getValue('xVal') + 1;
                                            }
                                        } else if (event.which === 40) {
                                            let containerSize = obj.getContainerContentSize();
                                            if ((obj.getValue('yVal') + obj.getValue('heightVal')) < containerSize.height) {
                                                val = obj.getValue('yVal') + 1;											
                                            }
                                        }
                                        if (val !== null) {
                                            let cmd = new SetValueCmd(selectionId, tagId, field,
                                                val, SetValueCmd.type.text, this);
                                            cmdGroup.addCommand(cmd);
                                        }
                                    }
                                }
                            }
                            if (!cmdGroup.isEmpty()) {
                                this.executeCommand(cmdGroup);
                            }
                            event.preventDefault();
                            break;
                        }
                    }
                }
            }
        });
    }

    /**
     * Adds default parameters like page count/number.
     */
    addDefaultParameters() {
        for (let parameterData of [
                { name: '页数', type: Parameter.type.number, eval: false, editable: false, showOnlyNameType: true },
                { name: '页码', type: Parameter.type.number, eval: false, editable: false, showOnlyNameType: true }]) {
            let parameter = new Parameter(this.getUniqueId(), parameterData, this);
            let parentPanel = this.mainPanel.getParametersItem();
            let panelItem = new MainPanelItem(
                'parameter', parentPanel, parameter, { hasChildren: false, showAdd: false, showDelete: false, draggable: false }, this);
            parameter.setPanelItem(panelItem);
            parentPanel.appendChild(panelItem);
            parameter.setup();
            this.addParameter(parameter);
        }
    }

    render() {
        this.element.empty();
        if (this.getProperty('menuSidebar')) {
            this.element.addClass('rbroMenuPanelSidebar');
        }
        this.element.append('<div class="rbroLogo"></div>');
        this.element.append('<div class="rbroMenuPanel" id="rbro_menu_panel"></div>');
        this.element.append(
            `<div class="rbroContainer">
                <div class="rbroMainPanel" id="rbro_main_panel"><ul id="rbro_main_panel_list"></ul></div>
                <div class="rbroMainPanelSizer" id="rbro_main_panel_sizer"></div>
                <div class="rbroDetailPanel" id="rbro_detail_panel"></div>
                <div class="rbroDocumentPanel" id="rbro_document_panel"></div>
            </div>`);
        this.mainPanel.render();
        this.menuPanel.render();
        for (let panelName in this.detailPanels) {
            this.detailPanels[panelName].render();
        }
        this.detailPanels[this.activeDetailPanel].show(this.detailData);
        this.document.render();
        this.popupWindow.render();
        this.updateMenuButtons();

        $(document).mouseup(event => {
            this.mainPanel.mouseUp(event);
            this.document.mouseUp(event);
            this.popupWindow.hide();
        });
        this.element
            .on('dragstart', event => {
                // disable dragging per default, otherwise e.g. a text selection can be dragged in Chrome
                event.preventDefault();
           })
           .mousemove(event => {
               if (!this.mainPanel.processMouseMove(event)) {
                   this.document.processMouseMove(event);
               }
           });
    }

    setup() {
        this.addDefaultParameters();
        this.headerBand.setup();
        this.contentBand.setup();
        this.footerBand.setup();
        this.documentProperties.setup();
    }

    initObjectMap() {
        this.addDataObject(this.headerBand);
        this.addDataObject(this.contentBand);
        this.addDataObject(this.footerBand);
        this.addDataObject(this.parameterContainer);
        this.addDataObject(this.styleContainer);
        this.addDataObject(this.documentProperties);
    }

    /**
     * Returns the label for given key.
     * @param {String} key
     * @returns {String} Label for given key, if it does not exist then the key is returned.
     */
    getLabel(key) {
        if (key in this.locale) {
            return this.locale[key];
        }
        return key;
    }

    getProperty(key) {
        return this.properties[key];
    }

    getMainPanel() {
        return this.mainPanel;
    }

    getDocument() {
        return this.document;
    }

    getPopupWindow() {
        return this.popupWindow;
    }

    getFonts() {
        return this.properties.fonts;
    }

    /**
     * Returns a list of all number and date patterns.
     * @returns {Object[]} Each item contains name (String), optional description (String) and optional separator (Boolean).
     */
    getPatterns() {
        let patterns = [];
        if (this.properties.patternNumbers.length > 0) {
            patterns.push({ separator: true, name: this.getLabel('patternSeparatorNumbers') });
            for (let pattern of this.properties.patternNumbers) {
                patterns.push(pattern);
            }
        }
        if (this.properties.patternDates.length > 0) {
            patterns.push({ separator: true, name: this.getLabel('patternSeparatorDates') });
            for (let pattern of this.properties.patternDates) {
                patterns.push(pattern);
            }
        }
        return patterns;
    }

    /**
     * Returns a list of parameter items.
     * Used for parameter popup window.
     * @param {DocElement|Parameter} obj - adds all parameters available for this object (which is either a doc element or a parameter).
     * For doc elements the parameters from the data source are included (e.g. array field parameters of a table data source).
     * @param {String[]} allowedTypes - specify allowed parameter types which will be added to the
     * parameters list. If not set all parameter types are allowed.
     * @returns {Object[]} Each item contains name (String), optional description (String) and
     * optional separator (Boolean).
     */
    getParameterItems(obj, allowedTypes) {
        let parameters = [];
        let parameterItems = this.getMainPanel().getParametersItem().getChildren();
        // dataSourceIndex is only needed for separator id which is used to hide the separator
        // when there are no data source parameters available (due to search filter)
        let dataSourceIndex = 0;
        let dataSources = [];
        if (obj instanceof DocElement) {
            obj.getAllDataSources(dataSources, null);
            for (let dataSource of dataSources) {
                if (dataSource.parameters.length > 0) {
                    parameters.push({
                        separator: true, separatorClass: 'rbroParameterDataSourceGroup', id: 'ds' + dataSourceIndex,
                        name: this.getLabel('parametersDataSource')
                    });
                    dataSourceIndex++;
                    for (let dataSourceParameter of dataSource.parameters) {
                        dataSourceParameter.appendParameterItems(parameters, allowedTypes);
                    }
                }
            }
        }

        parameters.push({ separator: true, name: this.getLabel('parameters') });
        let mapParameters = []; // add all parameters of collections at end of list with a header containing the collection name
        for (let parameterItem of parameterItems) {
            let parameter = parameterItem.getData();
            if (parameter.getValue('type') === Parameter.type.map) {
                parameter.appendParameterItems(mapParameters, allowedTypes);
            } else {
                parameter.appendParameterItems(parameters, allowedTypes);
            }
        }
        return parameters.concat(mapParameters);
    }

    /**
     * Returns a list of all array field parameter items.
     * Used for parameter popup window.
     * @param {String} fieldType - allowed parameter type which will be added to the
     * parameter list. If empty all parameter types are allowed.
     * @returns {Object[]} Each item contains name (String), optional description (String) and
     * optional separator (Boolean).
     */
    getArrayFieldParameterItems(fieldType) {
        let parameters = [];
        let parameterItems = this.getMainPanel().getParametersItem().getChildren();
        parameters.push({ separator: true, name: this.getLabel('parameters') });
        for (let parameterItem of parameterItems) {
            let parameter = parameterItem.getData();
            if (parameter.getValue('type') === Parameter.type.array) {
                parameter.appendFieldParameterItems(parameters, fieldType);
            }
        }
        return parameters;
    }

    /**
     * Append document elements of given container.
     * @param {Container} container
     * @param {Boolean} asObjects - if true the document element instances are returned, otherwise
     * each instance is transformed to a js map.
     * @param {DocElement[]} docElements - list where document elements will be appended to.
     */
    appendContainerDocElements(container, asObjects, docElements) {
        let children = container.getPanelItem().getChildren();
        for (let child of children) {
            if (child.getData() instanceof DocElement) {
                let docElement = child.getData();
                if (asObjects) {
                    docElements.push(docElement);
                    // we are also adding all internal children (document elements which belong
                    // to other document elements and cannot be created independently),
                    // e.g. a table band or a table cell (table text) of a table element.
                    docElement.addChildren(docElements);
                } else {
                    // js map also includes data of internal children
                    docElements.push(docElement.toJS());
                }
                let containers = [];
                if (docElement instanceof SectionElement) {
                    containers = docElement.getLinkedContainers();
                } else {
                    let linkedContainer = docElement.getLinkedContainer();
                    if (linkedContainer !== null) {
                        containers.push(linkedContainer);
                    }
                }
                // add children of doc elements which represent containers, e.g. frames or section bands
                for (let container of containers) {
                    this.appendContainerDocElements(container, asObjects, docElements);
                }
            }
        }
    };

    /**
     * Get document elements of all bands.
     * @param {Boolean} asObjects - if true the document element instances are returned, otherwise
     * each instance is transformed to a js map.
     * @returns {DocElement[]} List of document elements.
     */
    getDocElements(asObjects) {
        let docElements = [];
        this.appendContainerDocElements(this.headerBand, asObjects, docElements);
        this.appendContainerDocElements(this.contentBand, asObjects, docElements);
        this.appendContainerDocElements(this.footerBand, asObjects, docElements);
        return docElements;
    }

    setDetailPanel(panelName, data) {
        this.detailPanels[this.activeDetailPanel].hide();
        this.activeDetailPanel = panelName;
        this.detailData = data;
        this.detailPanels[panelName].show(data);
    }

    updateDetailPanel() {
        this.detailPanels[this.activeDetailPanel].updateData(this.detailData);
    }

    /**
     * Is called when a data object was modified (including new and deleted data objects).
     * @param {*} obj - new/deleted/modified data object.
     * @param {String} operation - operation which caused the notification.
     * @param {[String]} field - affected field in case of change operation.
     */
    notifyEvent(obj, operation, field) {
        if (obj instanceof Parameter) {
            if (obj.getValue('type') === Parameter.type.array || obj.getValue('type') === Parameter.type.map) {
                $(`#rbro_menu_item_add${obj.getId()}`).show();
                $(`#rbro_menu_item_children${obj.getId()}`).show();
                $(`#rbro_menu_item_children_toggle${obj.getId()}`).show();
            } else {
                $(`#rbro_menu_item_add${obj.getId()}`).hide();
                $(`#rbro_menu_item_children${obj.getId()}`).hide();
                $(`#rbro_menu_item_children_toggle${obj.getId()}`).hide();
            }
        } else if (obj instanceof Style) {
            if (operation === Command.operation.change) {
                for (let docElement of this.docElements) {
                    docElement.updateChangedStyle(obj.getId());
                }
            }
        }
        for (let panelName in this.detailPanels) {
            this.detailPanels[panelName].notifyEvent(obj, operation);
        }
    }	

    addParameter(parameter) {
        this.addDataObject(parameter);
    }

    addStyle(style) {
        this.addDataObject(style);
        this.notifyEvent(style, Command.operation.add);
    }

    getStyles() {
        let styles = [];
        for (let styleItem of this.getMainPanel().getStylesItem().getChildren()) {
            styles.push(styleItem.getData());
        }
        return styles;
    }

    getParameters() {
        let parameters = [];
        for (let parameterItem of this.getMainPanel().getParametersItem().getChildren()) {
            parameters.push(parameterItem.getData());
        }
        return parameters;
    }

    addDocElement(element) {
        this.docElements.push(element);
        this.addDataObject(element);
    }

    deleteDocElements() {
        for (let i=0; i < this.docElements.length; i++) {
            this.deleteDataObject(this.docElements[i]);
        }
        this.docElements = [];
    }

    getDetailData() {
        return this.detailData;
    }

    getDocumentProperties() {
        return this.documentProperties;
    }

    executeCommand(cmd) {
        cmd.do();
        if (this.lastCommandIndex < (this.commandStack.length - 1)) {
            this.commandStack = this.commandStack.slice(0, this.lastCommandIndex + 1);
        }
        if (!this.selectionSinceLastCommand && cmd instanceof SetValueCmd && this.commandStack.length > 0) {
            // if previous and current command are both SetValueCmds and target the same text field,
            // we can discard the previous command and only keep the latest update
            let prevCmd = this.commandStack[this.commandStack.length - 1];
            if (prevCmd instanceof SetValueCmd && prevCmd.allowReplace(cmd)) {
                cmd.oldValue = prevCmd.oldValue;
                this.commandStack = this.commandStack.slice(0, this.commandStack.length - 1);
                this.lastCommandIndex--;
            }
        }
        this.commandStack.push(cmd);
        this.lastCommandIndex++;
        this.modified = true;
        this.selectionSinceLastCommand = false;
        this.updateMenuButtons();
        if (this.properties.cmdExecutedCallback) {
            this.properties.cmdExecutedCallback(cmd);
        }
    }

    undoCommand() {
        if (this.lastCommandIndex >= 0) {
            let cmd = this.commandStack[this.lastCommandIndex];
            cmd.undo();
            this.lastCommandIndex--;
            this.modified = (this.lastCommandIndex >= 0);
            this.updateMenuButtons();
            if (this.properties.cmdExecutedCallback) {
                this.properties.cmdExecutedCallback(cmd);
            }
        }
    }

    redoCommand() {
        if (this.lastCommandIndex < (this.commandStack.length - 1)) {
            this.lastCommandIndex++;
            let cmd = this.commandStack[this.lastCommandIndex];
            cmd.do();
            this.modified = true;
            this.updateMenuButtons();
            if (this.properties.cmdExecutedCallback) {
                this.properties.cmdExecutedCallback(cmd);
            }
        }
    }

    updateMenuButtons() {
        $('#rbro_menu_save').prop('disabled', !this.modified);
        $('#rbro_menu_undo').prop('disabled', (this.lastCommandIndex < 0));
        $('#rbro_menu_redo').prop('disabled', (this.lastCommandIndex >= (this.commandStack.length - 1)));
    }

    updateMenuActionButtons() {
        let elementCount = 0;
        let previousContainerOffset = { x: 0, y: 0 };
        let elementSameContainerOffsetX = true;
        let elementSameContainerOffsetY = true;
        for (let selectionId of this.selections) {
            let obj = this.getDataObject(selectionId);
            if (obj instanceof DocElement && obj.getXTagId() !== '') {
                elementCount++;
                let container = obj.getContainer();
                let offset = container.getOffset();
                if (elementCount === 1) {
                    previousContainerOffset = offset;
                } else {
                    if (offset.x !== previousContainerOffset.x) {
                        elementSameContainerOffsetX = false;
                    }
                    if (offset.y !== previousContainerOffset.y) {
                        elementSameContainerOffsetY = false;
                    }
                }
            }
        }
        if (elementCount > 1) {
            // allow alignment of elements if their parent container has the same x/y offset
            if (elementSameContainerOffsetX) {
                $('#rbro_menu_align').show();
            } else {
                $('#rbro_menu_align').hide();
            }
            if (elementSameContainerOffsetY) {
                $('#rbro_menu_valign').show();
            } else {
                $('#rbro_menu_valign').hide();
            }
            $('#rbo_menu_elements .rbroMenuButton').hide();
            $('#rbro_menu_column_actions').hide();
            $('#rbro_menu_row_actions').hide();
        } else {
            let obj = null;
            if (this.selections.length === 1) {
                obj = this.getDataObject(this.selections[0]);
            }
            $('#rbro_menu_align').hide();
            $('#rbro_menu_valign').hide();
            if (obj instanceof TableTextElement) {
                $('#rbo_menu_elements .rbroMenuButton').hide();
                let table = obj.getTable();
                let parent = obj.getParent();
                if (table !== null && utils.convertInputToNumber(table.getValue('columns')) !== 1) {
                    $('#rbro_menu_column_delete').show();
                } else {
                    $('#rbro_menu_column_delete').hide();
                }
                $('#rbro_menu_column_actions').show();
                if (table !== null && parent !== null && parent.getValue('bandType') === Band.bandType.content) {
                    if (utils.convertInputToNumber(table.getValue('contentRows')) !== 1) {
                        $('#rbro_menu_row_delete').show();
                    } else {
                        $('#rbro_menu_row_delete').hide();
                    }
                    $('#rbro_menu_row_actions').show();
                } else {
                    $('#rbro_menu_row_actions').hide();
                }
            } else {
                $('#rbo_menu_elements .rbroMenuButton').show();
                $('#rbro_menu_column_actions').hide();
                $('#rbro_menu_row_actions').hide();
            }
        }
    }

    debugCommandStack() {
        console.clear();		
        for (let i=0; i < this.commandStack.length; i++) {
            if (i > this.lastCommandIndex) {
                console.log('( ' + i + ' ' + this.commandStack[i].getName() + ' )');
            } else {
                console.log(i + ' ' + this.commandStack[i].getName());
            }
        }
    }

    addDataObject(obj) {
        this.objectMap[obj.getId()] = obj;
    }

    deleteDataObject(obj) {
        if (this.isSelectedObject(obj.getId())) {
            this.deselectObject(obj.getId());
        }
        if (obj.getId() in this.objectMap) {
            obj.remove();
            delete this.objectMap[obj.getId()];
        }
    }

    getDataObject(id) {
        if (id !== null && id in this.objectMap) {
            return this.objectMap[id];
        }
        return null;
    }

    getSelectedObject() {
        if (this.selections.length === 1) {
            return this.getDataObject(this.selections[0]);
        }
        return null;
    }

    isSelectedObject(id) {
        return this.selections.indexOf(id) !== -1;
    }

    isDocElementSelected() {
        for (let selectionId of this.selections) {
            let obj = this.getDataObject(selectionId);
            if (obj instanceof DocElement) {
                return true;
            }
        }
        return false;
    }

    isTableElementSelected(tableId) {
        for (let selectionId of this.selections) {
            let obj = this.getDataObject(selectionId);
            if (obj instanceof TableTextElement) {
                if (obj.getValue('tableId') === tableId) {
                    return true;
                }
            }
        }
        return false;
    }

    selectObject(id, clearSelection) {
        if (clearSelection) {
            this.deselectAll();
        }
        let obj = this.getDataObject(id);
        if (obj !== null) {
            this.selections.push(id);
            obj.select();
            if (obj.getPanelItem() !== null) {
                obj.getPanelItem().openParentItems();
                obj.getPanelItem().setActive();
            }
        }
        this.selectionSinceLastCommand = true;
        this.updateMenuActionButtons();
    }

    deselectObject(id) {
        this.deselectObjectInternal(id, true);
        this.updateMenuActionButtons();
    }

    deselectObjectInternal(id, updateSelections) {
        let obj = this.getDataObject(id);
        if (obj !== null) {
            obj.deselect();
            if (this.detailData === obj) {
                this.setDetailPanel('none', null);
                $('.rbroMenuItem').removeClass('rbroMenuItemActive');
            }
        }
        if (updateSelections) {
            let selectionIndex = this.selections.indexOf(id);
            if (selectionIndex !== -1) {
                this.selections.splice(selectionIndex, 1);
            }
        }
    }

    deselectAll() {
        for (let selectionId of this.selections) {
            this.deselectObjectInternal(selectionId, false);
        }
        this.selections = [];
        this.updateMenuActionButtons();
    }

    getContainer(posX, posY, elementType) {
        let bestMatch = null;
        let bestMatchLevel = -1;
        for (let i = 0; i < this.containers.length; i++) {
            let container = this.containers[i];
            if (container.getLevel() > bestMatchLevel && container.isElementAllowed(elementType) &&
                    container.isInside(posX, posY)) {
                bestMatch = container;
                bestMatchLevel = container.getLevel();
            }
        }
        return bestMatch;
    }

    addContainer(container) {
        this.containers.push(container);
        this.addDataObject(container);
    }

    deleteContainer(container) {
        for (let i = 0; i < this.containers.length; i++) {
            if (this.containers[i].getId() === container.getId()) {
                this.containers.splice(i, 1);
                break;
            }
        }
        this.deleteDataObject(container);
    }

    /**
     * Store our own drag data because dataTransfer data of event is not available in
     * dragenter/dragover/dragleave events (in some browsers).
     */
    startBrowserDrag(browserDragType, browserDragElementType, browserDragId) {
        this.browserDragType = browserDragType;
        this.browserDragId = browserDragId;
        this.getDocument().startBrowserDrag(browserDragElementType);
    }

    isBrowserDragActive(browserDragType) {
        return this.browserDragType === browserDragType;
    }

    getBrowserDragId() {
        return this.browserDragId;
    }

    updateSelectionDrag(diffX, diffY, dragType, dragContainer, store) {
        let cmdGroup;
        if (store) {
            cmdGroup = new CommandGroupCmd(dragType === DocElement.dragType.element ? 'Update position' : 'Resize', this);
        }
        for (let selectionId of this.selections) {
            let obj = this.getDataObject(selectionId);
            if (obj !== null) {
                if (dragType !== DocElement.dragType.element || obj.isDraggingAllowed()) {
                    obj.updateDrag(diffX, diffY, dragType, dragContainer, store ? cmdGroup : null);
                }
            }
        }
        if (store && !cmdGroup.isEmpty()) {
            this.executeCommand(cmdGroup);
        }
    }

    /**
     * Aligns all currently selected doc elements to each other.
     * @param {Style.alignment} alignment
     */
    alignSelections(alignment) {
        let alignVal = NaN;
        let x, y, width, height;
        let minX = Number.MAX_VALUE, maxX = Number.MIN_VALUE, minY = Number.MAX_VALUE, maxY = Number.MIN_VALUE;
        let elementCount = 0;
        for (let selectionId of this.selections) {
            let obj = this.getDataObject(selectionId);
            if (obj instanceof DocElement && obj.getXTagId() !== '') {
                elementCount++;
                x = obj.getValue('xVal');
                y = obj.getValue('yVal');
                width = obj.getValue('widthVal');
                height = obj.getValue('heightVal');
                if (x < minX) {
                    minX = x;
                }
                if ((x + width) > maxX) {
                    maxX = x + width;
                }
                if (y < minY) {
                    minY = y;
                }
                if ((y + height) > maxY) {
                    maxY = y + height;
                }
            }
        }
        let center = minX + ((maxX - minX) / 2);
        let vcenter  = minY + ((maxY - minY) / 2);
        if (elementCount > 1) {
            let cmdGroup = new CommandGroupCmd('Align elements', this);
            for (let selectionId of this.selections) {
                let obj = this.getDataObject(selectionId);
                if (obj instanceof DocElement && !(obj instanceof PageBreakElement)) {
                    switch (alignment) {
                        case Style.alignment.left: {
                            let cmd = new SetValueCmd(obj.getId(), obj.getXTagId(), 'x',
                                '' + minX, SetValueCmd.type.text, this);
                            cmdGroup.addCommand(cmd);
                        }
                        break;
                        case Style.alignment.center: {
                            let cmd = new SetValueCmd(obj.getId(), obj.getXTagId(), 'x',
                                '' + (center - (obj.getValue('widthVal') / 2)), SetValueCmd.type.text, this);
                            cmdGroup.addCommand(cmd);
                        }
                        break;
                        case Style.alignment.right: {
                            let cmd = new SetValueCmd(obj.getId(), obj.getXTagId(), 'x',
                                '' + (maxX - obj.getValue('widthVal')), SetValueCmd.type.text, this);
                            cmdGroup.addCommand(cmd);
                        }
                        break;
                        case Style.alignment.top: {
                            let cmd = new SetValueCmd(obj.getId(), obj.getYTagId(), 'y',
                                '' + minY, SetValueCmd.type.text, this);
                            cmdGroup.addCommand(cmd);
                        }
                        break;
                        case Style.alignment.middle: {
                            let cmd = new SetValueCmd(obj.getId(), obj.getYTagId(), 'y',
                                '' + (vcenter - (obj.getValue('heightVal') / 2)), SetValueCmd.type.text, this);
                            cmdGroup.addCommand(cmd);
                        }
                        break;
                        case Style.alignment.bottom: {
                            let cmd = new SetValueCmd(obj.getId(), obj.getYTagId(), 'y',
                                '' + (maxY - obj.getValue('heightVal')), SetValueCmd.type.text, this);
                            cmdGroup.addCommand(cmd);
                        }
                        break;
                    }
                }
            }
            this.executeCommand(cmdGroup);
        }
    }

    /**
     * Converts given value to a string which can be used in css style attribute
     * where a position or size must be specified.
     * @param {String|Number} val - a number value, can also be given as a string.
     * @returns {String}
     */
    toPixel(val) {
        if (val === '') {
            return '0px';
        }
        if ($.type(val) === 'string') {
            val = parseFloat(val.replace(',', '.'));
            if (isNaN(val)) {
                return '0px';
            }
        }
        return val + 'px';
    }

    /**
     * Shows a global loading image which disables all controls.
     */
    showLoading() {
        if ($('#rbro_loading_div').length == 0) {
            $('body').append('<div id="rbro_loading_div" class="rbroLoadingIndicator"></div>');
        }
    }

    /**
     * Hides global loading image.
     */
    hideLoading() {
        $('#rbro_loading_div').remove();
    }

    getTestData() {
        let ret = {};
        for (let parameter of this.getParameters()) {
            if (!parameter.getValue('showOnlyNameType')) {
                let type = parameter.getValue('type');
                if (type === Parameter.type.map) {
                    let testData = {};
                    for (let child of parameter.getChildren()) {
                        testData[child.getName()] = child.getValue('testData');
                    }
                    ret[parameter.getName()] = testData;
                } else if (type === Parameter.type.array) {
                    ret[parameter.getName()] = parameter.getTestDataRows(false);
                } else if (type === Parameter.type.simpleArray) {
                    let testDataRows = [];
                    // because test data rows are stored as map items we convert the list to a list of simple values
                    for (let testDataRow of parameter.getTestDataRows(false)) {
                        if ('data' in testDataRow) {
                            testDataRows.push(testDataRow['data']);
                        }
                    }
                    ret[parameter.getName()] = testDataRows;
                } else if (type === Parameter.type.string || type === Parameter.type.number ||
                           type === Parameter.type.boolean || type === Parameter.type.date) {
                    ret[parameter.getName()] = parameter.getValue('testData');
                }
            }
        }
        return ret;
    }

    processErrors(errors) {
        for (let error of errors) {
            if (error.object_id) {
                $(`#rbro_menu_item${error.object_id}`).addClass('rbroError');
                let obj = this.getDataObject(error.object_id);
                if (obj !== null) {
                    obj.addError(error);
                }
            }
        }
        if (errors.length > 0) {
            this.detailPanels[this.activeDetailPanel].updateErrors();
            this.selectObject(errors[0].object_id, true);
        }
    }

    /**
     * Performs ajax request to upload the report and either update displayed errors or
     * display report pdf in case report is valid.
     * @param {Object} data - report data.
     * @param {Boolean} isTestData - true if data contains test data from parameters.
     */
    previewInternal(data, isTestData) {
        // hct.yc
        // outputFormat, data, isTestData
        let self = this;
        $('.rbroMenuItem').removeClass('rbroError');
        for (var objId in this.objectMap) {
            this.objectMap[objId].clearErrors();
        }
        this.detailPanels[this.activeDetailPanel].updateErrors();
        this.showLoading();
        var info = {
            report: this.getReport(),
            // hct.yc
            // outputFormat: outputFormat,
            data: data,
            isTestData: isTestData
        }
        $.ajax('/report/put', {
            data: {'info': JSON.stringify(info)},
            type: "POST",
            timeout: this.properties.reportServerTimeout,
            crossDomain: this.properties.reportServerUrlCrossDomain,
            success: function success(data) {
                self.hideLoading();
                var pdfPrefix = 'data:application/pdf';
                if (data.substr(0, 4) === 'key:') {
                    self.reportKey = data.substr(4);
                    self.getDocument().openPdfPreviewTab('/report/get?key=' + self.reportKey + '&outputFormat=pdf');
                } else {
                    self.reportKey = null;
                    try {
                        var obj = JSON.parse(data);
                        if (obj.errors.length > 0) {
                            alert(obj.errors);
                        }
                    } catch (e) {
                        alert('报表打印失败，请联系客服');
                    }
                }
            },
            error: function error(jqXHR, textStatus, errorThrown) {
                self.hideLoading();
                if (textStatus === "timeout") {
                    alert('preview failed (timeout)');
                } else {
                    alert('preview failed');
                }
            }
        });
    }

    ///////////////////////////////////////////////////////////////////////////
    // API functions
    ///////////////////////////////////////////////////////////////////////////

    /**
     * Sets the internal modified flag.
     * If true the save button is enabled, otherwise the save button is disabled.
     * @param {Boolean} modified
     */
    setModified(modified) {
        this.modified = modified;
        this.updateMenuButtons();
    }

    /**
     * Returns report object containing everything needed for the report.
     * @returns {Object}
     */
    getReport() {
        let ret = { docElements: [], parameters: [], styles: [], version: 3 };
        let i;
        ret.docElements = this.getDocElements(false);
        for (let parameter of this.getParameters()) {
            ret.parameters.push(parameter.toJS());
        }
        for (let style of this.getStyles()) {
            ret.styles.push(style.toJS());
        }
        ret.documentProperties = this.documentProperties.toJS();
        
        return ret;
    }

    /**
     * Either calls saveCallback (if available) or stores report in local storage (if key is available).
     */
    save() {
        if (this.properties.saveCallback) {
            this.properties.saveCallback();
        } else if (this.properties.localStorageReportKey) {
            if ('localStorage' in window && window['localStorage'] !== null) {
                try {
                    let report = this.getReport();
                    // console.log(JSON.stringify(report));
                    // hct.yc
                    // var ss = (0, _stringify2.default)(report);
                    // var active_id = false;
                    // var reg = new RegExp("(^|&)active_id=([^&]*)(&|$)");
                    // var r = window.location.search.substr(1).match(reg);
                    // if(r != null) {
                    //     active_id = unescape(r[2]);
                    // }
                    // $.ajax({
                    //     url : '/save/designer',
                    //     data: {content: ss,active_id: active_id},
                    //     cache : false,
                    //     async : false,
                    //     type : "POST",
                    //     success : function (result){
                    //         var json = eval("(" + result + ")");
                    //         if (json.flag == false) {
                    //             alert("保存失败，请联系管理员");
                    //         }
                    //     },
                    // });
                    window.localStorage.setItem(this.properties.localStorageReportKey, JSON.stringify(report));
                    this.modified = false;
                } catch (e) {
                }
            }
        }
        this.updateMenuButtons();
    }

    /**
     * Loads report object into ReportBro Designer.
     * @param {Object} report - the report object.
     */
    load(report) {
        for (let parameter of this.getParameters()) {
            this.deleteDataObject(parameter);
        }
        for (let style of this.getStyles()) {
            this.deleteDataObject(style);
        }
        this.deleteDocElements();

        this.nextId = 1;
        this.setDetailPanel('none', null);
        this.docElements = [];
        this.objectMap = {};
        this.initObjectMap();
        this.selections = [];
        this.getMainPanel().clearAll();
        this.getMainPanel().getHeaderItem().close();
        this.getMainPanel().getDocumentItem().close();
        this.getMainPanel().getFooterItem().close();
        this.getMainPanel().getParametersItem().close();
        this.getMainPanel().getStylesItem().close();

        if (report.version < 2) {
            for (let docElementData of report.docElements) {
                if (docElementData.elementType === DocElement.type.table) {
                    docElementData.contentDataRows = [docElementData.contentData];
                    docElementData.contentRows = '1';
                }
            }
        }
        if (report.version < 3) {
            for (let docElementData of report.docElements) {
                if (docElementData.elementType === DocElement.type.table) {
                    let width = 0;
                    for (let i=0; i < docElementData.headerData.columnData.length; i++) {
                        width += docElementData.headerData.columnData[i].width;
                    }
                    docElementData.width = width;
                }
            }
        }

        this.documentProperties.setInitialData(report.documentProperties);
        this.documentProperties.setup();

        for (let styleData of report.styles) {
            this.createStyle(styleData);
        }
        for (let parameterData of report.parameters) {
            this.createParameter(parameterData);
        }
        for (let docElementData of report.docElements) {
            this.createDocElement(docElementData);
        }

        this.browserDragType = '';
        this.browserDragId = '';

        this.commandStack = [];
        this.lastCommandIndex = -1;
        this.modified = false;
        this.updateMenuButtons();
    }

    /**
     * Loads report from local storage (if key and report is available).
     */
    loadLocalReport() {
        if (this.properties.localStorageReportKey) {
            if ('localStorage' in window && window['localStorage'] !== null) {
                let report = null;
                try {
                    report = JSON.parse(window.localStorage[this.properties.localStorageReportKey]);
                } catch (e) {
                }
                if (report !== null) {
                    this.load(report);
                }
            }
        }
    }
  
    preview() {
        this.previewInternal(this.getTestData(), true);
        // hct.yc
        // this.previewInternal(_DocumentProperties2.default.outputFormat.pdf, this.getTestData(), true);
    }

    previewWithData(data) {
        this.previewInternal(data, false);
        // hct.yc
        // this.previewInternal(_DocumentProperties2.default.outputFormat.pdf, data, false);
    }

    /**
     * Downloads spreadsheet file for a report where a preview was executed before.
     */
    downloadSpreadsheet() {
        if (this.reportKey !== null) {
            window.open(this.properties.reportServerUrl + '?key=' + this.reportKey + '&outputFormat=xlsx', '_blank');
        }
    }

    /**
     * Returns a new unique id which can be used for any data object.
     * @returns {Number}
     */
    getUniqueId() {
        return this.nextId++;
    }

    /**
     * Returns document element for the given id, or null if document element does not exist.
     * @param {Number} id - Id of document element to search for.
     * @returns {[DocElement]}
     */
    getDocElementById(id) {
        let obj = this.getDataObject(id);
        if (obj instanceof DocElement) {
            return obj;
        }
        return null;
    }

    /**
     * Returns parameter for the given id, or null if parameter does not exist.
     * @param {Number} id - Id of parameter to search for.
     * @returns {[Parameter]}
     */
    getParameterById(id) {
        let obj = this.getDataObject(id);
        if (obj instanceof Parameter) {
            return obj;
        }
        return null;
    }

    /**
     * Returns parameter for the given name, or null if parameter does not exist.
     * @param {String} parameterName - Name of parameter to search for.
     * @returns {[Parameter]}
     */
    getParameterByName(parameterName) {
        let parameters = this.getParameters();
        for (let parameter of parameters) {
            if (parameter.getValue('name') === parameterName) {
                return parameter;
            }
        }
        return null;
    }

    /**
     * Returns style for the given id, or null if style does not exist.
     * @param {Number} id - Id of style to search for.
     * @returns {[Style]}
     */
    getStyleById(id) {
        let obj = this.getDataObject(id);
        if (obj instanceof Style) {
            return obj;
        }
        return null;
    }

    /**
     * Creates a doc element with given data.
     * @param {Object} docElementData - Map containing all data for new doc element, must
     * also contain a unique id.
     * @returns {DocElement} the created doc element.
     */
    createDocElement(docElementData) {
        let element = AddDeleteDocElementCmd.createElement(
            docElementData.id, docElementData, docElementData.elementType, -1, false, this);
        let maxId = element.getMaxId();
        if (maxId >= this.nextId) {
            this.nextId = maxId + 1;
        }
        return element;
    }

    /**
     * Creates a parameter with given data.
     * @param {Object} parameterData - Map containing all data for new parameter, must
     * also contain an unique id.
     * @returns {Parameter} the created parameter.
     */
    createParameter(parameterData) {
        let parameter = new Parameter(parameterData.id, parameterData, this);
        let parentPanel = this.mainPanel.getParametersItem();
        let panelItem = new MainPanelItem(
            'parameter', parentPanel, parameter,
            { hasChildren: true, showAdd: parameter.getValue('editable'), showDelete: parameter.getValue('editable'), draggable: true }, this);
        parameter.setPanelItem(panelItem);
        parentPanel.appendChild(panelItem);
        parameter.setup();
        if (parameter.getValue('type') !== Parameter.type.array && parameter.getValue('type') !== Parameter.type.map) {
            $(`#rbro_menu_item_add${parameter.getId()}`).hide();
            $(`#rbro_menu_item_children${parameter.getId()}`).hide();
            $(`#rbro_menu_item_children_toggle${parameter.getId()}`).hide();
        }
        this.addParameter(parameter);
        let maxId = parameter.getMaxId();
        if (maxId >= this.nextId) {
            this.nextId = maxId + 1;
        }
        return parameter;
    }

    /**
     * Creates a style with given data.
     * @param {Object} styleData - Map containing all data for new style, must
     * also contain an unique id.
     * @returns {Style} the created style.
     */
    createStyle(styleData) {
        let style = new Style(styleData.id, styleData, this);
        let parentPanel = this.mainPanel.getStylesItem();
        let panelItem = new MainPanelItem('style', parentPanel, style, { draggable: true }, this);
        style.setPanelItem(panelItem);
        parentPanel.appendChild(panelItem);
        this.addStyle(style);
        if (styleData.id >= this.nextId) {
            this.nextId = styleData.id + 1;
        }
        return style;
    }

    /**
     * Deletes given doc element. Deletes internal object and all
     * related GUI elements (panel item, layout element).
     * @param {DocElement} element - doc element to delete.
     */
    deleteDocElement(element) {
        for (let i=0; i < this.docElements.length; i++) {
            if (this.docElements[i].getId() === element.getId()) {
                this.notifyEvent(element, Command.operation.remove);
                if (this.detailData === this.docElements[i]) {
                    this.setDetailPanel('none', null);
                }
                this.docElements.splice(i, 1);
                this.deleteDataObject(element);
                break;
            }
        }
    }

    /**
     * Deletes given parameter. Deletes internal object and all
     * related GUI elements (panel item, layout element).
     * @param {Parameter} parameter - parameter to delete.
     */
    deleteParameter(parameter) {
        this.notifyEvent(parameter, Command.operation.remove);
        this.deleteDataObject(parameter);
        parameter.getPanelItem().getParent().removeChild(parameter.getPanelItem());
    }

    /**
     * Deletes given style. Deletes internal object and all
     * related GUI elements (panel item, layout element).
     * @param {Style} style - style to delete.
     */
    deleteStyle(style) {
        this.notifyEvent(style, Command.operation.remove);
        this.deleteDataObject(style);
        style.getPanelItem().getParent().removeChild(style.getPanelItem());
    }
}
