import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, message, Tooltip, Divider } from 'antd';
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
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { clearCache } from '../api/stockApi';
import './MainLayout.css';

const { Header, Content, Sider } = Layout;

const MainLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedKeys, setSelectedKeys] = useState(['1']);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const path = location.pathname;
    if (path.startsWith('/a-share/industries')) {
      setSelectedKeys(['8']);
    } else if (path.startsWith('/a-share')) {
      setSelectedKeys(['1']);
    } else if (path.startsWith('/us-stock')) {
      setSelectedKeys(['2']);
    } else if (path.startsWith('/crypto')) {
      setSelectedKeys(['3']);
    } else if (path.startsWith('/commodities')) {
      setSelectedKeys(['4']);
    } else if (path.startsWith('/futures')) {
      setSelectedKeys(['5']);
    } else if (path.startsWith('/options')) {
      setSelectedKeys(['6']);
    } else if (path.startsWith('/backtest')) {
      setSelectedKeys(['7']);
    } else if (path.startsWith('/screener')) {
      setSelectedKeys(['9']);
    } else {
      setSelectedKeys(['1']);
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

  const menuItems = [
    {
      key: '1',
      icon: <LineChartOutlined />,
      label: 'A股市场',
      onClick: () => navigate('/a-share'),
    },
    {
      key: '2',
      icon: <DollarOutlined />,
      label: '美股市场',
      onClick: () => navigate('/us-stock'),
    },
    {
      key: '3',
      icon: <GlobalOutlined />,
      label: '加密货币',
      onClick: () => navigate('/crypto'),
    },
    {
      key: '4',
      icon: <GoldOutlined />,
      label: '大宗商品',
      onClick: () => navigate('/commodities'),
    },
    {
      key: '5',
      icon: <GoldOutlined />,
      label: '期货',
      onClick: () => navigate('/futures'),
    },
    {
      key: '6',
      icon: <GoldOutlined />,
      label: '期权',
      onClick: () => navigate('/options'),
    },
    {
      key: '7',
      icon: <ExperimentOutlined />,
      label: '回溯测试',
      onClick: () => navigate('/backtest'),
    },
    {
      key: '8',
      icon: <LineChartOutlined />,
      label: 'A股行业',
      onClick: () => navigate('/a-share/industries'),
    },
    {
      key: '9',
      icon: <FilterOutlined />,
      label: '股票筛选器',
      onClick: () => navigate('/screener'),
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
          <h2 style={{ margin: 0 }}>金融回归测试工具</h2>
        </Header>
        <Content className="main-content">
          <div className="main-content-inner">{children}</div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;