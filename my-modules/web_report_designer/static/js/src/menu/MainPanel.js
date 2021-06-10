import MainPanelItem from './MainPanelItem';
import Container from '../container/Container';
import Document from '../Document';

/**
 * Main panel which contains all report elements like doc elements, parameters and styles.
 * The main panel shows the structure and all components of the report.
 * @class
 */
export default class MainPanel {
    constructor(rootElement, headerBand, contentBand, footerBand, parameterContainer, styleContainer, rb) {
        this.rootElement = rootElement;
        this.rb = rb;
        this.headerItem = new MainPanelItem(
            'band', null, headerBand,
            { hasChildren: true, showAdd: false, showDelete: false, hasDetails: false, visible: this.rb.getDocumentProperties().getValue('header') }, rb);
        
        this.documentItem = new MainPanelItem(
            'band', null, contentBand,
            { hasChildren: true, showAdd: false, showDelete: false, hasDetails: false }, rb);
        
        this.footerItem = new MainPanelItem(
            'band', null, footerBand,
            { hasChildren: true, showAdd: false, showDelete: false, hasDetails: false, visible: this.rb.getDocumentProperties().getValue('footer') }, rb);

        this.parametersItem = new MainPanelItem(
            'parameter', null, parameterContainer,
            { hasChildren: true, showAdd: rb.getProperty('adminMode'), showDelete: false, hasDetails: false }, rb);

        this.stylesItem = new MainPanelItem(
            'style', null, styleContainer,
            { hasChildren: true, showAdd: true, showDelete: false, hasDetails: false }, rb);
        
        this.documentPropertiesItem = new MainPanelItem(
            'documentProperties', null, rb.getDocumentProperties(), { showDelete: false, hasDetails: true }, rb);
        
        this.items = [
            this.headerItem,
            this.documentItem,
            this.footerItem,
            this.parametersItem,
            this.stylesItem,
            this.documentPropertiesItem
        ];

        this.dragMainPanelSizer = false;
        this.dragMainPanelSizerStartX = 0;
        this.mainPanelWidth = 230;
        this.mainPanelSizerWidth = 3;

        headerBand.setPanelItem(this.headerItem);
        contentBand.setPanelItem(this.documentItem);
        footerBand.setPanelItem(this.footerItem);
        parameterContainer.setPanelItem(this.parametersItem);
        styleContainer.setPanelItem(this.stylesItem);
    }

    getHeaderItem() {
        return this.headerItem;
    }

    getDocumentItem() {
        return this.documentItem;
    }

    getFooterItem() {
        return this.footerItem;
    }

    getParametersItem() {
        return this.parametersItem;
    }

    getStylesItem() {
        return this.stylesItem;
    }

    getContainerByItem(item) {
        while (item !== null) {
            if (item.getData() instanceof Container) {
                return item.getData();
            }
            item = item.getParent();
        }
        return null;
    }

    getDocumentPropertiesItem() {
        return this.documentPropertiesItem;
    }

    render() {
        let panel = $('#rbro_main_panel_list');
        this.appendChildren(panel, this.items);

        $('#rbro_main_panel_sizer').mousedown(event => {
            this.dragMainPanelSizer =  true;
            this.dragMainPanelSizerStartX = event.pageX;
        });

        this.updateMainPanelWidth(this.mainPanelWidth);
    }

    appendChildren(el, items) {
        for (let item of items) {
            el.append(item.getElement());
            let children = item.getChildren();
            if (children.length > 0) {
                let elChildren = $(`#${item.getId()}_children`);
                this.appendChildren(el, children);
            }
        }
    }

    processMouseMove(event) {
        if (this.dragMainPanelSizer) {
            let mainPanelWidth = this.mainPanelWidth + (event.pageX - this.dragMainPanelSizerStartX);
            mainPanelWidth = this.checkMainPanelWidth(mainPanelWidth);
            this.updateMainPanelWidth(mainPanelWidth);
            return true;
        }
        return false;
    }

    mouseUp(event) {
        if (this.dragMainPanelSizer) {
            this.dragMainPanelSizer = false;
            this.mainPanelWidth = this.mainPanelWidth + (event.pageX - this.dragMainPanelSizerStartX);
            this.mainPanelWidth = this.checkMainPanelWidth(this.mainPanelWidth);
            this.updateMainPanelWidth(this.mainPanelWidth);
        }
    }

    updateMainPanelWidth(mainPanelWidth) {
        $('#rbro_main_panel').css({ width: mainPanelWidth });
        $('#rbro_main_panel_sizer').css({ left: mainPanelWidth });
        $('#rbro_detail_panel').css({ left: mainPanelWidth + this.mainPanelSizerWidth });
        // calculate width of main panel, detail panel and sidebar (if available)
        let totalPanelWidth = mainPanelWidth + this.mainPanelSizerWidth + 390;
        if (this.rb.getProperty('menuSidebar')) {
            totalPanelWidth += 104;
            $('#reportbro .rbroLogo').css({ width: mainPanelWidth });
        }
        $('#rbro_document_panel').css({ width: `calc(100% - ${totalPanelWidth}px)` });
    }

    checkMainPanelWidth(mainPanelWidth) {
        if (mainPanelWidth < 150) {
            return 150;
        } else if (mainPanelWidth > 500) {
            return 500;
        }
        return mainPanelWidth;
    }

    showHeader() {
        this.headerItem.show();
    }

    hideHeader() {
        this.headerItem.hide();
    }

    showFooter() {
        this.footerItem.show();
    }

    hideFooter() {
        this.footerItem.hide();
    }

    clearAll() {
        for (let item of this.items) {
            item.clear();
        }
    }
}
