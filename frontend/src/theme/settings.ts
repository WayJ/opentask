/** Default theme settings */
export const themeSettings: App.Theme.ThemeSetting = {
  themeScheme: 'light',
  grayscale: false,
  colourWeakness: false,
  recommendColor: false,
  themeColor: '#5e6ad2',
  themeRadius: 6,
  otherColor: {
    info: '#2080f0',
    success: '#27a644',
    warning: '#faad14',
    error: '#f5222d'
  },
  isInfoFollowPrimary: true,
  layout: {
    mode: 'vertical',
    scrollMode: 'content'
  },
  page: {
    animate: true,
    animateMode: 'fade-slide'
  },
  header: {
    height: 56,
    breadcrumb: {
      visible: true,
      showIcon: true
    },
    multilingual: {
      visible: true
    },
    globalSearch: {
      visible: true
    }
  },
  tab: {
    visible: true,
    cache: true,
    height: 40,
    mode: 'chrome',
    closeTabByMiddleClick: false
  },
  fixedHeaderAndTab: true,
  sider: {
    inverted: false,
    width: 220,
    collapsedWidth: 64,
    mixWidth: 90,
    mixCollapsedWidth: 64,
    mixChildMenuWidth: 200,
    autoSelectFirstMenu: false
  },
  footer: {
    visible: false,
    fixed: false,
    height: 48,
    right: true
  },
  watermark: {
    visible: false,
    text: 'OpenTask',
    enableUserName: false,
    enableTime: false,
    timeFormat: 'YYYY-MM-DD HH:mm'
  },
  tokens: {
    light: {
      colors: {
        container: 'rgb(255, 255, 255)',
        layout: 'rgb(245, 246, 246)',
        inverted: 'rgb(1, 1, 2)',
        'base-text': 'rgb(0, 0, 0)'
      },
      boxShadow: {
        header: '0 1px 0 rgb(230, 231, 232)',
        sider: '1px 0 0 rgb(230, 231, 232)',
        tab: '0 1px 0 rgb(230, 231, 232)'
      }
    },
    dark: {
      colors: {
        container: 'rgb(15, 16, 17)',
        layout: 'rgb(1, 1, 2)',
        'base-text': 'rgb(247, 248, 248)'
      },
      boxShadow: {
        header: '0 1px 0 rgb(35, 37, 42)',
        sider: '1px 0 0 rgb(35, 37, 42)',
        tab: '0 1px 0 rgb(35, 37, 42)'
      }
    }
  }
};

/**
 * Override theme settings
 *
 * If publish new version, use `overrideThemeSettings` to override certain theme settings
 */
export const overrideThemeSettings: Partial<App.Theme.ThemeSetting> = {};
