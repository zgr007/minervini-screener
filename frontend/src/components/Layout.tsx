import React, { useState } from 'react'
import { Layout, Menu, Typography, Badge, Space, theme } from 'antd'
import {
  DashboardOutlined,
  SearchOutlined,
  StarOutlined,
  BarChartOutlined,
  WalletOutlined,
  HistoryOutlined,
  ExperimentOutlined,
  SettingOutlined,
  BellOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout
const { Text } = Typography

interface AppLayoutProps {
  children: React.ReactNode
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { token } = theme.useToken()

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: '/screen', icon: <SearchOutlined />, label: '选股结果' },
    { key: '/watchlist', icon: <StarOutlined />, label: '观察列表' },
    { key: '/positions', icon: <WalletOutlined />, label: '持仓管理' },
    { key: '/trades', icon: <HistoryOutlined />, label: '交易日志' },
    { key: '/backtest', icon: <ExperimentOutlined />, label: '回测系统' },
    { key: '/settings', icon: <SettingOutlined />, label: '系统设置' },
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        width={220}
        style={{
          background: token.colorBgContainer,
          borderRight: `1px solid ${token.colorBorderSecondary}`,
        }}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Text strong style={{ fontSize: collapsed ? 14 : 16, color: token.colorPrimary }}>
            {collapsed ? 'MS' : 'Minervini Screener'}
          </Text>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <Space>
            <Badge status="success" text={<Text type="secondary">系统运行中</Text>} />
          </Space>
          <Space>
            <BellOutlined style={{ fontSize: 18, cursor: 'pointer' }} />
          </Space>
        </Header>
        <Content
          style={{
            margin: 16,
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
            minHeight: 280,
          }}
        >
          {children}
        </Content>
      </Layout>
    </Layout>
  )
}

export default AppLayout
