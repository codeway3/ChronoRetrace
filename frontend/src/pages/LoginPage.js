import React, { useState, useEffect } from 'react';
import { Form, Input, Button, Card, Typography, Divider, Checkbox, message } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './LoginPage.css';

const { Title, Text } = Typography;

const LoginPage = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const { login, register, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  // 如果已经登录，重定向到主页
  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from?.pathname || '/a-share';
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, location]);

  // 处理登录
  const handleLogin = async (values) => {
    setLoading(true);
    try {
      const result = await login({
        username: values.username,
        password: values.password
      });
      
      if (result.success) {
        const from = location.state?.from?.pathname || '/a-share';
        navigate(from, { replace: true });
      }
    } catch (error) {
      console.error('Login error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 处理注册
  const handleRegister = async (values) => {
    setLoading(true);
    try {
      const result = await register({
        username: values.username,
        email: values.email,
        password: values.password,
        full_name: values.fullName
      });
      
      if (result.success) {
        setIsRegisterMode(false);
        form.resetFields();
        message.success('注册成功！请登录您的账户。');
      }
    } catch (error) {
      console.error('Register error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 切换登录/注册模式
  const toggleMode = () => {
    setIsRegisterMode(!isRegisterMode);
    form.resetFields();
  };

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="login-overlay"></div>
      </div>
      
      <Card className="login-card">
        <div className="login-header">
          <Title level={2} className="login-title">
            ChronoRetrace
          </Title>
          <Text className="login-subtitle">
            {isRegisterMode ? '创建新账户' : '登录您的账户'}
          </Text>
        </div>

        <Form
          form={form}
          name={isRegisterMode ? 'register' : 'login'}
          onFinish={isRegisterMode ? handleRegister : handleLogin}
          layout="vertical"
          size="large"
          className="login-form"
        >
          {isRegisterMode && (
            <Form.Item
              name="fullName"
              label="姓名"
              rules={[
                { required: true, message: '请输入您的姓名！' },
                { min: 2, message: '姓名至少需要2个字符！' }
              ]}
            >
              <Input
                prefix={<UserOutlined />}
                placeholder="请输入您的姓名"
              />
            </Form.Item>
          )}

          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名！' },
              { min: 3, message: '用户名至少需要3个字符！' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线！' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="请输入用户名"
            />
          </Form.Item>

          {isRegisterMode && (
            <Form.Item
              name="email"
              label="邮箱"
              rules={[
                { required: true, message: '请输入邮箱地址！' },
                { type: 'email', message: '请输入有效的邮箱地址！' }
              ]}
            >
              <Input
                prefix={<MailOutlined />}
                placeholder="请输入邮箱地址"
              />
            </Form.Item>
          )}

          <Form.Item
            name="password"
            label="密码"
            rules={isRegisterMode ? [
              { required: true, message: '请输入密码！' },
              { min: 8, message: '密码至少需要8个字符！' },
              {
                pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                message: '密码必须包含大小写字母、数字和特殊字符！'
              }
            ] : [
              { required: true, message: '请输入密码！' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请输入密码"
            />
          </Form.Item>

          {isRegisterMode && (
            <Form.Item
              name="confirmPassword"
              label="确认密码"
              dependencies={['password']}
              rules={[
                { required: true, message: '请确认密码！' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('password') === value) {
                      return Promise.resolve();
                    }
                    return Promise.reject(new Error('两次输入的密码不一致！'));
                  },
                }),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="请再次输入密码"
              />
            </Form.Item>
          )}

          {!isRegisterMode && (
            <Form.Item>
              <div className="login-options">
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox>记住我</Checkbox>
                </Form.Item>
                <Link to="/forgot-password" className="forgot-password-link">
                  忘记密码？
                </Link>
              </div>
            </Form.Item>
          )}

          {isRegisterMode && (
            <Form.Item
              name="agreement"
              valuePropName="checked"
              rules={[
                {
                  validator: (_, value) =>
                    value ? Promise.resolve() : Promise.reject(new Error('请同意用户协议！')),
                },
              ]}
            >
              <Checkbox>
                我已阅读并同意 <Link to="/terms">用户协议</Link> 和 <Link to="/privacy">隐私政策</Link>
              </Checkbox>
            </Form.Item>
          )}

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              className="login-button"
            >
              {isRegisterMode ? '注册' : '登录'}
            </Button>
          </Form.Item>
        </Form>

        <Divider className="login-divider">
          <Text type="secondary">或</Text>
        </Divider>

        <div className="login-footer">
          <Text>
            {isRegisterMode ? '已有账户？' : '还没有账户？'}
            <Button type="link" onClick={toggleMode} className="toggle-mode-button">
              {isRegisterMode ? '立即登录' : '立即注册'}
            </Button>
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;