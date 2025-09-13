import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Form,
  Input,
  Button,
  Avatar,
  Upload,
  Select,
  DatePicker,
  Switch,
  Divider,
  Row,
  Col,
  Typography,
  message,
  Tabs
} from 'antd';
import {
  UserOutlined,
  MailOutlined,
  PhoneOutlined,
  EditOutlined,
  LockOutlined,
  UploadOutlined,
  SafetyOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../api/authApi';
import moment from 'moment';
import './ProfilePage.css';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

const ProfilePage = () => {
  const [profileForm] = Form.useForm();
  const [passwordForm] = Form.useForm();
  const [preferencesForm] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [preferencesLoading, setPreferencesLoading] = useState(false);
  const [avatarUrl, setAvatarUrl] = useState('');
  const { user, updateProfile, changePassword } = useAuth();

  // 加载用户偏好设置
  const loadPreferences = useCallback(async () => {
    try {
      const response = await authApi.getPreferences();
      const prefs = response.data;
      preferencesForm.setFieldsValue(prefs);
    } catch (error) {
      console.error('Failed to load preferences:', error);
    }
  }, [preferencesForm]);

  useEffect(() => {
    loadPreferences();
  }, [loadPreferences]);

  // 设置表单初始值
  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({
        username: user.username,
        email: user.email,
        full_name: user.full_name,
        phone: user.phone,
        birth_date: user.birth_date ? moment(user.birth_date) : null,
        gender: user.gender,
        profession: user.profession,
        investment_experience: user.investment_experience
      });
      setAvatarUrl(user.avatar_url || '');
    }
  }, [user, profileForm]);



  // 更新用户资料
  const handleUpdateProfile = async (values) => {
    setLoading(true);
    try {
      const updateData = {
        ...values,
        birth_date: values.birth_date ? values.birth_date.format('YYYY-MM-DD') : null,
        avatar_url: avatarUrl
      };
      
      await updateProfile(updateData);
    } catch (error) {
      console.error('Update profile error:', error);
    } finally {
      setLoading(false);
    }
  };

  // 修改密码
  const handleChangePassword = async (values) => {
    setPasswordLoading(true);
    try {
      await changePassword({
        current_password: values.currentPassword,
        new_password: values.newPassword
      });
      passwordForm.resetFields();
    } catch (error) {
      console.error('Change password error:', error);
    } finally {
      setPasswordLoading(false);
    }
  };

  // 更新偏好设置
  const handleUpdatePreferences = async (values) => {
    setPreferencesLoading(true);
    try {
      await authApi.updatePreferences(values);
      message.success('偏好设置更新成功！');
    } catch (error) {
      const errorMessage = error.response?.data?.detail || '更新失败，请稍后重试';
      message.error(errorMessage);
    } finally {
      setPreferencesLoading(false);
    }
  };

  // 头像上传处理
  const handleAvatarChange = (info) => {
    if (info.file.status === 'uploading') {
      return;
    }
    if (info.file.status === 'done') {
      // 这里应该从服务器响应中获取图片URL
      const url = info.file.response?.url || URL.createObjectURL(info.file.originFileObj);
      setAvatarUrl(url);
      message.success('头像上传成功！');
    } else if (info.file.status === 'error') {
      message.error('头像上传失败！');
    }
  };

  // 上传前验证
  const beforeUpload = (file) => {
    const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
    if (!isJpgOrPng) {
      message.error('只能上传 JPG/PNG 格式的图片！');
      return false;
    }
    const isLt2M = file.size / 1024 / 1024 < 2;
    if (!isLt2M) {
      message.error('图片大小不能超过 2MB！');
      return false;
    }
    return true;
  };

  return (
    <div className="profile-container">
      <Card className="profile-header-card">
        <div className="profile-header">
          <div className="avatar-section">
            <Avatar
              size={100}
              src={avatarUrl}
              icon={<UserOutlined />}
              className="profile-avatar"
            />
            <Upload
              name="avatar"
              showUploadList={false}
              action="/api/v1/upload/avatar"
              beforeUpload={beforeUpload}
              onChange={handleAvatarChange}
              className="avatar-upload"
            >
              <Button icon={<UploadOutlined />} size="small">
                更换头像
              </Button>
            </Upload>
          </div>
          <div className="profile-info">
            <Title level={3}>{user?.full_name || user?.username}</Title>
            <Text type="secondary">{user?.email}</Text>
            <div className="user-badges">
              {user?.vip_level > 0 && (
                <span className={`vip-badge vip-${user.vip_level}`}>
                  {user.vip_level === 1 ? 'VIP' : 'Premium'}
                </span>
              )}
              {user?.email_verified && (
                <span className="verified-badge">已验证</span>
              )}
            </div>
          </div>
        </div>
      </Card>

      <Card className="profile-content-card">
        <Tabs defaultActiveKey="profile" className="profile-tabs">
          <TabPane tab="个人资料" key="profile" icon={<UserOutlined />}>
            <Form
              form={profileForm}
              layout="vertical"
              onFinish={handleUpdateProfile}
              className="profile-form"
            >
              <Row gutter={24}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="username"
                    label="用户名"
                    rules={[
                      { required: true, message: '请输入用户名！' },
                      { min: 3, message: '用户名至少需要3个字符！' }
                    ]}
                  >
                    <Input prefix={<UserOutlined />} disabled />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="email"
                    label="邮箱"
                    rules={[
                      { required: true, message: '请输入邮箱！' },
                      { type: 'email', message: '请输入有效的邮箱地址！' }
                    ]}
                  >
                    <Input prefix={<MailOutlined />} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col xs={24} sm={12}>
                  <Form.Item
                    name="full_name"
                    label="姓名"
                    rules={[{ required: true, message: '请输入姓名！' }]}
                  >
                    <Input prefix={<UserOutlined />} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item name="phone" label="手机号">
                    <Input prefix={<PhoneOutlined />} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col xs={24} sm={8}>
                  <Form.Item name="birth_date" label="出生日期">
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="gender" label="性别">
                    <Select placeholder="请选择性别">
                      <Option value="male">男</Option>
                      <Option value="female">女</Option>
                      <Option value="other">其他</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="profession" label="职业">
                    <Input placeholder="请输入职业" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col xs={24} sm={12}>
                  <Form.Item name="investment_experience" label="投资经验">
                    <Select placeholder="请选择投资经验">
                      <Option value="beginner">初学者</Option>
                      <Option value="intermediate">中级</Option>
                      <Option value="advanced">高级</Option>
                      <Option value="expert">专家</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  icon={<EditOutlined />}
                >
                  更新资料
                </Button>
              </Form.Item>
            </Form>
          </TabPane>

          <TabPane tab="安全设置" key="security" icon={<LockOutlined />}>
            <div className="security-section">
              <Title level={4}>修改密码</Title>
              <Form
                form={passwordForm}
                layout="vertical"
                onFinish={handleChangePassword}
                className="password-form"
              >
                <Form.Item
                  name="currentPassword"
                  label="当前密码"
                  rules={[{ required: true, message: '请输入当前密码！' }]}
                >
                  <Input.Password prefix={<LockOutlined />} />
                </Form.Item>

                <Form.Item
                  name="newPassword"
                  label="新密码"
                  rules={[
                    { required: true, message: '请输入新密码！' },
                    { min: 8, message: '密码至少需要8个字符！' },
                    {
                      pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
                      message: '密码必须包含大小写字母、数字和特殊字符！'
                    }
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} />
                </Form.Item>

                <Form.Item
                  name="confirmPassword"
                  label="确认新密码"
                  dependencies={['newPassword']}
                  rules={[
                    { required: true, message: '请确认新密码！' },
                    ({ getFieldValue }) => ({
                      validator(_, value) {
                        if (!value || getFieldValue('newPassword') === value) {
                          return Promise.resolve();
                        }
                        return Promise.reject(new Error('两次输入的密码不一致！'));
                      },
                    }),
                  ]}
                >
                  <Input.Password prefix={<LockOutlined />} />
                </Form.Item>

                <Form.Item>
                  <Button
                    type="primary"
                    htmlType="submit"
                    loading={passwordLoading}
                    icon={<SafetyOutlined />}
                  >
                    修改密码
                  </Button>
                </Form.Item>
              </Form>

              <Divider />

              <div className="two-factor-section">
                <Title level={4}>双因子认证</Title>
                <div className="two-factor-item">
                  <div className="two-factor-info">
                    <Text strong>双因子认证</Text>
                    <br />
                    <Text type="secondary">
                      为您的账户添加额外的安全保护
                    </Text>
                  </div>
                  <Switch
                    checked={user?.two_factor_enabled}
                    onChange={(checked) => {
                      // 处理双因子认证开关
                      console.log('2FA toggle:', checked);
                    }}
                  />
                </div>
              </div>
            </div>
          </TabPane>

          <TabPane tab="偏好设置" key="preferences" icon={<EditOutlined />}>
            <Form
              form={preferencesForm}
              layout="vertical"
              onFinish={handleUpdatePreferences}
              className="preferences-form"
            >
              <Row gutter={24}>
                <Col xs={24} sm={12}>
                  <Form.Item name="theme_mode" label="主题模式">
                    <Select>
                      <Option value="light">浅色</Option>
                      <Option value="dark">深色</Option>
                      <Option value="auto">自动</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item name="language" label="语言">
                    <Select>
                      <Option value="zh-CN">简体中文</Option>
                      <Option value="en-US">English</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={24}>
                <Col xs={24} sm={12}>
                  <Form.Item name="currency" label="默认货币">
                    <Select>
                      <Option value="CNY">人民币 (CNY)</Option>
                      <Option value="USD">美元 (USD)</Option>
                      <Option value="EUR">欧元 (EUR)</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item name="timezone" label="时区">
                    <Select>
                      <Option value="Asia/Shanghai">北京时间</Option>
                      <Option value="America/New_York">纽约时间</Option>
                      <Option value="Europe/London">伦敦时间</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">通知设置</Divider>

              <Row gutter={24}>
                <Col xs={24} sm={8}>
                  <Form.Item name="email_notifications" label="邮件通知" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="sms_notifications" label="短信通知" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="push_notifications" label="推送通知" valuePropName="checked">
                    <Switch />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="left">投资偏好</Divider>

              <Row gutter={24}>
                <Col xs={24} sm={12}>
                  <Form.Item name="risk_tolerance" label="风险承受能力">
                    <Select>
                      <Option value="conservative">保守型</Option>
                      <Option value="moderate">稳健型</Option>
                      <Option value="aggressive">激进型</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item name="investment_horizon" label="投资期限">
                    <Select>
                      <Option value="short_term">短期 (&lt; 1年)</Option>
                      <Option value="medium_term">中期 (1-5年)</Option>
                      <Option value="long_term">长期 (&gt; 5年)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={preferencesLoading}
                  icon={<EditOutlined />}
                >
                  保存偏好设置
                </Button>
              </Form.Item>
            </Form>
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default ProfilePage;