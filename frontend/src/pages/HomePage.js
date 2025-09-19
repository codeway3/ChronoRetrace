import React, { useState, useEffect } from 'react';
import { Button, Typography, Row, Col, Card, Space } from 'antd';
import { 
  LineChartOutlined, 
  BarChartOutlined, 
  SearchOutlined, 
  SafetyOutlined,
  RocketOutlined,
  LoginOutlined,
  UserAddOutlined,
  ArrowRightOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './HomePage.css';

const { Title, Paragraph } = Typography;

const HomePage = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [animationClass, setAnimationClass] = useState('');

  // 如果已登录，重定向到主页面
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/a-share', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // 页面加载动画
  useEffect(() => {
    setAnimationClass('fade-in');
  }, []);

  const features = [
    {
      icon: <LineChartOutlined style={{ fontSize: '48px', color: '#1890ff' }} />,
      title: '多市场数据分析',
      description: '支持A股、美股、加密货币等多个市场的实时数据获取和分析，提供全面的市场洞察。'
    },
    {
      icon: <BarChartOutlined style={{ fontSize: '48px', color: '#52c41a' }} />,
      title: '策略回测系统',
      description: '强大的回测引擎，支持自定义投资策略测试，提供详细的性能指标和风险分析。'
    },
    {
      icon: <SearchOutlined style={{ fontSize: '48px', color: '#faad14' }} />,
      title: '智能股票筛选',
      description: '基于技术指标和基本面数据的高级筛选系统，快速发现符合条件的投资机会。'
    },
    {
      icon: <SafetyOutlined style={{ fontSize: '48px', color: '#f5222d' }} />,
      title: '安全可靠',
      description: '采用JWT认证、Redis缓存等企业级技术栈，确保数据安全和系统稳定性。'
    }
  ];

  const handleLogin = () => {
    navigate('/login');
  };

  const handleRegister = () => {
    navigate('/login', { state: { mode: 'register' } });
  };

  return (
    <div className={`homepage ${animationClass}`}>
      {/* 顶部导航栏 */}
      <div className="homepage-header">
        <div className="header-content">
          <div className="logo-section">
            <RocketOutlined className="logo-icon" />
            <span className="logo-text">ChronoRetrace</span>
          </div>
          <div className="auth-buttons">
            <Space size="middle">
              <Button 
                type="default" 
                icon={<LoginOutlined />}
                onClick={handleLogin}
                className="auth-btn login-btn"
              >
                登录
              </Button>
              <Button 
                type="primary" 
                icon={<UserAddOutlined />}
                onClick={handleRegister}
                className="auth-btn register-btn"
              >
                注册
              </Button>
            </Space>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="homepage-content">
        {/* Hero Section */}
        <div className="hero-section">
          <div className="hero-content">
            <div className="hero-text">
              <Title level={1} className="hero-title">
                <span className="gradient-text">ChronoRetrace</span>
              </Title>
              <Title level={2} className="hero-subtitle">
                专业的金融数据分析与回测平台
              </Title>
              <Paragraph className="hero-description">
                为量化分析师、投资者和开发者提供强大的金融数据分析工具。
                支持多市场数据获取、策略回测、智能筛选等功能，助您在投资路上更进一步。
              </Paragraph>
              <div className="hero-actions">
                <Button 
                  type="primary" 
                  size="large"
                  icon={<ArrowRightOutlined />}
                  onClick={handleLogin}
                  className="cta-button"
                >
                  立即开始
                </Button>
                <Button 
                  type="default" 
                  size="large"
                  onClick={handleRegister}
                  className="secondary-button"
                >
                  还没有账号？注册
                </Button>
              </div>
            </div>
            <div className="hero-visual">
              <div className="floating-cards">
                {/* 实时数据卡片 */}
                <div className="feature-tip tip-1">
                  <div className="tip-icon-wrapper">
                    <LineChartOutlined className="tip-icon" />
                  </div>
                  <div className="tip-content">
                    <h4>实时数据</h4>
                    <p>多市场数据源</p>
                  </div>
                  <div className="tip-glow"></div>
                </div>

                {/* 策略回测卡片 */}
                <div className="feature-tip tip-2">
                  <div className="tip-icon-wrapper">
                    <BarChartOutlined className="tip-icon" />
                  </div>
                  <div className="tip-content">
                    <h4>策略回测</h4>
                    <p>历史数据验证</p>
                  </div>
                  <div className="tip-glow"></div>
                </div>

                {/* 智能筛选卡片 */}
                <div className="feature-tip tip-3">
                  <div className="tip-icon-wrapper">
                    <SearchOutlined className="tip-icon" />
                  </div>
                  <div className="tip-content">
                    <h4>智能筛选</h4>
                    <p>AI驱动分析</p>
                  </div>
                  <div className="tip-glow"></div>
                </div>

                {/* 背景装饰元素 */}
                <div className="visual-decoration">
                  <div className="decoration-circle circle-1"></div>
                  <div className="decoration-circle circle-2"></div>
                  <div className="decoration-circle circle-3"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 功能特性区域 */}
        <div className="features-section">
          <div className="section-content">
            <Title level={2} className="section-title">
              核心功能特性
            </Title>
            <Row gutter={[32, 32]} className="features-grid">
              {features.map((feature, index) => (
                <Col xs={24} sm={12} lg={6} key={index}>
                  <Card 
                    className="feature-card"
                    hoverable
                    variant="borderless"
                  >
                    <div className="feature-icon">
                      {feature.icon}
                    </div>
                    <Title level={4} className="feature-title">
                      {feature.title}
                    </Title>
                    <Paragraph className="feature-description">
                      {feature.description}
                    </Paragraph>
                  </Card>
                </Col>
              ))}
            </Row>
          </div>
        </div>

        {/* CTA区域 */}
        <div className="cta-section">
          <div className="cta-content">
            <Title level={2} className="cta-title">
              准备开始您的量化投资之旅？
            </Title>
            <Paragraph className="cta-description">
              加入我们，体验专业的金融数据分析平台
            </Paragraph>
            <Space size="large">
              <Button 
                type="primary" 
                size="large"
                icon={<LoginOutlined />}
                onClick={handleLogin}
                className="cta-primary"
              >
                立即登录
              </Button>
              <Button 
                type="default" 
                size="large"
                icon={<UserAddOutlined />}
                onClick={handleRegister}
                className="cta-secondary"
              >
                免费注册
              </Button>
            </Space>
          </div>
        </div>
      </div>

      {/* 页脚 */}
      <div className="homepage-footer">
        <div className="footer-content">
          <Paragraph className="footer-text">
            © 2024 ChronoRetrace. 基于 MIT 许可证开源
          </Paragraph>
        </div>
      </div>
    </div>
  );
};

export default HomePage;