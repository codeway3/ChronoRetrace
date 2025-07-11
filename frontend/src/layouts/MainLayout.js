import React from 'react';
import { Layout, Menu } from 'antd';
import { LineChartOutlined, DollarOutlined, GlobalOutlined } from '@ant-design/icons';

const { Header, Content, Sider } = Layout;

const MainLayout = ({ children }) => {
  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        breakpoint="lg"
        collapsedWidth="0"
      >
        <div style={{ height: '32px', margin: '16px', background: 'rgba(255, 255, 255, 0.2)', color: 'white', textAlign: 'center', lineHeight: '32px', borderRadius: '6px' }}>
            ChronoRetrace
        </div>
        <Menu theme="dark" mode="inline" defaultSelectedKeys={['1']}>
          <Menu.Item key="1" icon={<LineChartOutlined />}>
            A-Share Market
          </Menu.Item>
          <Menu.Item key="2" icon={<DollarOutlined />} disabled>
            US Market (Soon)
          </Menu.Item>
          <Menu.Item key="3" icon={<GlobalOutlined />} disabled>
            Crypto (Soon)
          </Menu.Item>
        </Menu>
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 16px' }}>
            <h2 style={{margin: 0}}>Financial Regression Testing Tool</h2>
        </Header>
        <Content style={{ margin: '24px 16px 0' }}>
          <div style={{ padding: 24, background: '#fff', minHeight: 360 }}>
            {children}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
