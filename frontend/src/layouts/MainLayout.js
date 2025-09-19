import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, message, Tooltip, Divider, Dropdown, Avatar, Space } from 'antd';
import {
  LineChartOutlined,
  DollarOutlined,
  GlobalOutlined,
  GoldOutlined,
  DeleteOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ExperimentOutlined,
  FilterOutlined,
  UserOutlined,
  LogoutOutlined,
  SettingOutlined,
  BarChartOutlined,
  FundOutlined,
  StockOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { clearCache } from '../api/stockApi';
import { useAuth } from '../contexts/AuthContext';
import './MainLayout.css';

const { Header, Content, Sider } = Layout;

const MainLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedKeys, setSelectedKeys] = useState(['a-share-dashboard']);
  const [openKeys, setOpenKeys] = useState(['a-share']);
  const [collapsed, setCollapsed] = useState(false);
  const { user, logout } = useAuth();

  useEffect(() => {
    const path = location.pathname;

    // 根据路径设置选中的菜单项和展开的子菜单
    if (path.startsWith('/a-share/industries')) {
      setSelectedKeys(['a-share-industries']);
      setOpenKeys(['a-share']);
    } else if (path.startsWith('/a-share/screener')) {
      setSelectedKeys(['a-share-screener']);
      setOpenKeys(['a-share']);
    } else if (path.startsWith('/a-share/backtest')) {
      setSelectedKeys(['a-share-backtest']);
      setOpenKeys(['a-share']);
    } else if (path.startsWith('/a-share')) {
      setSelectedKeys(['a-share-dashboard']);
      setOpenKeys(['a-share']);
    } else if (path.startsWith('/us-stock/screener')) {
      setSelectedKeys(['us-stock-screener']);
      setOpenKeys(['us-stock']);
    } else if (path.startsWith('/us-stock/backtest')) {
      setSelectedKeys(['us-stock-backtest']);
      setOpenKeys(['us-stock']);
    } else if (path.startsWith('/us-stock')) {
      setSelectedKeys(['us-stock-dashboard']);
      setOpenKeys(['us-stock']);
    } else if (path.startsWith('/crypto/screener')) {
      setSelectedKeys(['crypto-screener']);
      setOpenKeys(['crypto']);
    } else if (path.startsWith('/crypto/backtest')) {
      setSelectedKeys(['crypto-backtest']);
      setOpenKeys(['crypto']);
    } else if (path.startsWith('/crypto')) {
      setSelectedKeys(['crypto-dashboard']);
      setOpenKeys(['crypto']);
    } else if (path.startsWith('/commodities/screener')) {
      setSelectedKeys(['commodities-screener']);
      setOpenKeys(['commodities']);
    } else if (path.startsWith('/commodities/backtest')) {
      setSelectedKeys(['commodities-backtest']);
      setOpenKeys(['commodities']);
    } else if (path.startsWith('/commodities')) {
      setSelectedKeys(['commodities-dashboard']);
      setOpenKeys(['commodities']);
    } else if (path.startsWith('/futures/screener')) {
      setSelectedKeys(['futures-screener']);
      setOpenKeys(['futures']);
    } else if (path.startsWith('/futures/backtest')) {
      setSelectedKeys(['futures-backtest']);
      setOpenKeys(['futures']);
    } else if (path.startsWith('/futures')) {
      setSelectedKeys(['futures-dashboard']);
      setOpenKeys(['futures']);
    } else if (path.startsWith('/options/screener')) {
      setSelectedKeys(['options-screener']);
      setOpenKeys(['options']);
    } else if (path.startsWith('/options/backtest')) {
      setSelectedKeys(['options-backtest']);
      setOpenKeys(['options']);
    } else if (path.startsWith('/options')) {
      setSelectedKeys(['options-dashboard']);
      setOpenKeys(['options']);
    } else if (path.startsWith('/screener')) {
      setSelectedKeys(['screener']);
    } else if (path.startsWith('/backtest')) {
      setSelectedKeys(['backtest']);
    } else {
      setSelectedKeys(['a-share-dashboard']);
      setOpenKeys(['a-share']);
    }
  }, [location.pathname]);

  const handleClearCache = async () => {
    try {
      const response = await clearCache();
      message.success(response.data.message || 'Cache cleared successfully!');
    } catch (error) {
      message.error('Failed to clear cache.');
      console.error('Failed to clear cache:', error);
    }
  };

  const handleLogout = async () => {
    try {
      await logout();
      message.success('退出登录成功');
      navigate('/login');
    } catch (error) {
      message.error('退出登录失败');
      console.error('Logout error:', error);
    }
  };

  const menuItems = [
    {
      key: 'a-share',
      icon: <LineChartOutlined />,
      label: 'A股市场',
      children: [
        {
          key: 'a-share-dashboard',
          icon: <BarChartOutlined />,
          label: '市场概览',
          onClick: () => navigate('/a-share'),
        },
        {
          key: 'a-share-screener',
          icon: <FilterOutlined />,
          label: '股票筛选',
          onClick: () => navigate('/a-share/screener'),
        },
        {
          key: 'a-share-backtest',
          icon: <ExperimentOutlined />,
          label: '回溯测试',
          onClick: () => navigate('/a-share/backtest'),
        },
        {
          key: 'a-share-industries',
          icon: <StockOutlined />,
          label: '行业分析',
          onClick: () => navigate('/a-share/industries'),
        },
      ],
    },
    {
      key: 'us-stock',
      icon: <DollarOutlined />,
      label: '美股市场',
      children: [
        {
          key: 'us-stock-dashboard',
          icon: <BarChartOutlined />,
          label: '市场概览',
          onClick: () => navigate('/us-stock'),
        },
        {
          key: 'us-stock-screener',
          icon: <FilterOutlined />,
          label: '股票筛选',
          onClick: () => navigate('/us-stock/screener'),
        },
        {
          key: 'us-stock-backtest',
          icon: <ExperimentOutlined />,
          label: '回溯测试',
          onClick: () => navigate('/us-stock/backtest'),
        },
      ],
    },
    {
      key: 'crypto',
      icon: <GlobalOutlined />,
      label: '加密货币',
      children: [
        {
          key: 'crypto-dashboard',
          icon: <BarChartOutlined />,
          label: '市场概览',
          onClick: () => navigate('/crypto'),
        },
        {
          key: 'crypto-screener',
          icon: <FilterOutlined />,
          label: '币种筛选',
          onClick: () => navigate('/crypto/screener'),
        },
        {
          key: 'crypto-backtest',
          icon: <ExperimentOutlined />,
          label: '回溯测试',
          onClick: () => navigate('/crypto/backtest'),
        },
      ],
    },
    {
      key: 'commodities',
      icon: <GoldOutlined />,
      label: '大宗商品',
      children: [
        {
          key: 'commodities-dashboard',
          icon: <BarChartOutlined />,
          label: '市场概览',
          onClick: () => navigate('/commodities'),
        },
        {
          key: 'commodities-screener',
          icon: <FilterOutlined />,
          label: '商品筛选',
          onClick: () => navigate('/commodities/screener'),
        },
        {
          key: 'commodities-backtest',
          icon: <ExperimentOutlined />,
          label: '回溯测试',
          onClick: () => navigate('/commodities/backtest'),
        },
      ],
    },
    {
      key: 'futures',
      icon: <FundOutlined />,
      label: '期货',
      children: [
        {
          key: 'futures-dashboard',
          icon: <BarChartOutlined />,
          label: '市场概览',
          onClick: () => navigate('/futures'),
        },
        {
          key: 'futures-screener',
          icon: <FilterOutlined />,
          label: '期货筛选',
          onClick: () => navigate('/futures/screener'),
        },
        {
          key: 'futures-backtest',
          icon: <ExperimentOutlined />,
          label: '回溯测试',
          onClick: () => navigate('/futures/backtest'),
        },
      ],
    },
    {
      key: 'options',
      icon: <StockOutlined />,
      label: '期权',
      children: [
        {
          key: 'options-dashboard',
          icon: <BarChartOutlined />,
          label: '市场概览',
          onClick: () => navigate('/options'),
        },
        {
          key: 'options-screener',
          icon: <FilterOutlined />,
          label: '期权筛选',
          onClick: () => navigate('/options/screener'),
        },
        {
          key: 'options-backtest',
          icon: <ExperimentOutlined />,
          label: '回溯测试',
          onClick: () => navigate('/options/backtest'),
        },
      ],
    },
    {
      type: 'divider',
    },
    {
      key: 'screener',
      icon: <FilterOutlined />,
      label: '通用筛选器',
      onClick: () => navigate('/screener'),
    },
    {
      key: 'backtest',
      icon: <ExperimentOutlined />,
      label: '通用回测',
      onClick: () => navigate('/backtest'),
    },
  ];

  const siderWidth = collapsed ? 80 : 200;

  return (
    <Layout className="main-layout">
      <Sider
        className="sidebar"
        collapsible
        collapsed={collapsed}
        trigger={null}
        breakpoint="lg"
        onBreakpoint={setCollapsed}
        collapsedWidth="80"
        width={200}
      >
        <div className="sidebar-container">
          <div className="sidebar-body">
            <div className={`logo ${collapsed ? 'collapsed' : ''}`}>
              {collapsed ? 'CR' : 'ChronoRetrace'}
            </div>
            <Menu
              theme="dark"
              mode="inline"
              selectedKeys={selectedKeys}
              openKeys={openKeys}
              onOpenChange={setOpenKeys}
              items={menuItems}
            />
          </div>
          <div className="sidebar-footer">
            <div className={`clear-cache-wrapper ${collapsed ? 'collapsed' : ''}`}>
              <Tooltip title={collapsed ? '清除缓存' : ''} placement="right">
                <Button
                  type="primary"
                  danger
                  block
                  icon={<DeleteOutlined />}
                  onClick={handleClearCache}
                >
                  {!collapsed && '清除缓存'}
                </Button>
              </Tooltip>
            </div>
            <Divider className="sidebar-divider" />
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className={`collapse-button ${collapsed ? 'collapsed' : ''}`}
            >
              {!collapsed && '收起侧栏'}
            </Button>
          </div>
        </div>
      </Sider>
      <Layout className="content-layout" style={{ marginLeft: siderWidth }}>
        <Header className="main-header">
          <div className="header-content" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: '100%' }}>
            <h2 style={{ margin: 0 }}>金融回归测试工具</h2>
            <Space>
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'profile',
                      icon: <UserOutlined />,
                      label: '个人资料',
                      onClick: () => navigate('/profile')
                    },
                    {
                      key: 'settings',
                      icon: <SettingOutlined />,
                      label: '设置'
                    },
                    {
                      type: 'divider'
                    },
                    {
                      key: 'logout',
                      icon: <LogoutOutlined />,
                      label: '退出登录',
                      onClick: handleLogout
                    }
                  ]
                }}
                placement="bottomRight"
                trigger={['click']}
              >
                <Button type="text" className="user-menu-trigger">
                  <Space>
                    <Avatar
                      size="small"
                      src={user?.avatar_url}
                      icon={<UserOutlined />}
                    />
                    <span className="username">{user?.full_name || user?.username}</span>
                  </Space>
                </Button>
              </Dropdown>
            </Space>
          </div>
        </Header>
        <Content className="main-content">
          <div className="main-content-inner">{children}</div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
