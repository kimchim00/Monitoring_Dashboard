// src/Dashboard.tsx
import React, { useState } from 'react';
import {
  Layout, Menu, Card, Statistic, Row, Col, Table, Typography, Spin, Alert, List, Tag, Empty,
} from 'antd';
import {
  DashboardOutlined, LineChartOutlined, WarningOutlined, ClockCircleOutlined,
  UserOutlined, BellOutlined, GlobalOutlined, MobileOutlined, ApiOutlined,
} from '@ant-design/icons';
import { Line } from '@ant-design/plots';
import type { ColumnsType } from 'antd/es/table';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

// ── Mock Data ────────────────────────────────────────────────────────────────

// Overview Trend (simple time series)
const mockTrendData = [
  { time: '00:00', responseTime: 0.8, errorRate: 0.2 },
  { time: '04:00', responseTime: 1.1, errorRate: 0.5 },
  { time: '08:00', responseTime: 1.4, errorRate: 1.2 },
  { time: '12:00', responseTime: 0.9, errorRate: 0.4 },
  { time: '16:00', responseTime: 1.6, errorRate: 2.1 },
  { time: '20:00', responseTime: 1.2, errorRate: 0.8 },
  { time: '24:00', responseTime: 0.7, errorRate: 0.3 },
];

// Recent Issues
const mockIssues = [
  { key: '1', time: '2 mins ago', severity: 'Critical', message: 'API /checkout timeout > 5s (Germany)' },
  { key: '2', time: '18 mins ago', severity: 'Warning', message: 'LCP > 4s on mobile (3.2% users)' },
  { key: '3', time: '47 mins ago', severity: 'Info', message: 'SSL certificate renews in 12 days' },
];

// Errors Table
const mockErrors = [
  { key: '1', timestamp: '2026-01-29 01:45', type: 'JS', message: 'Uncaught TypeError: Cannot read properties of null', endpoint: '/product/123', users: '142 (4.1%)' },
  { key: '2', timestamp: '2026-01-29 01:32', type: 'Server', message: '500 Internal Server Error', endpoint: '/api/payment', users: '89 (2.6%)' },
];

// Uptime Checks
const mockUptime = [
  { key: '1', site: 'Main Site', status: 'Up', uptime: '99.98%', lastDown: 'Never', response: '420ms' },
  { key: '2', site: 'API EU', status: 'Up', uptime: '99.91%', lastDown: 'Jan 15, 3min', response: '680ms' },
];

// RUM Table (Core Web Vitals)
const mockVitals = [
  { key: '1', metric: 'LCP', p75: '2.1s', rating: 'Good', mobile: '2.4s', desktop: '1.8s' },
  { key: '2', metric: 'INP', p75: '180ms', rating: 'Good', mobile: '210ms', desktop: '150ms' },
  { key: '3', metric: 'CLS', p75: '0.08', rating: 'Good', mobile: '0.11', desktop: '0.05' },
];

// ── Columns ──────────────────────────────────────────────────────────────────
const errorColumns: ColumnsType<typeof mockErrors[0]> = [
  { title: 'Time', dataIndex: 'timestamp', key: 'timestamp' },
  { title: 'Type', dataIndex: 'type', key: 'type' },
  { title: 'Message', dataIndex: 'message', key: 'message', ellipsis: true },
  { title: 'Endpoint', dataIndex: 'endpoint', key: 'endpoint' },
  { title: 'Affected Users', dataIndex: 'users', key: 'users' },
];

const uptimeColumns: ColumnsType<typeof mockUptime[0]> = [
  { title: 'Site', dataIndex: 'site', key: 'site' },
  { title: 'Status', dataIndex: 'status', key: 'status', render: (text) => <Tag color={text === 'Up' ? 'success' : 'error'}>{text}</Tag> },
  { title: 'Uptime (30d)', dataIndex: 'uptime', key: 'uptime' },
  { title: 'Last Down', dataIndex: 'lastDown', key: 'lastDown' },
  { title: 'Avg Response', dataIndex: 'response', key: 'response' },
];

const vitalsColumns: ColumnsType<typeof mockVitals[0]> = [
  { title: 'Metric', dataIndex: 'metric', key: 'metric' },
  { title: 'P75 Value', dataIndex: 'p75', key: 'p75' },
  { title: 'Rating', dataIndex: 'rating', key: 'rating', render: (text) => <Tag color={text === 'Good' ? 'success' : text === 'Needs Improvement' ? 'warning' : 'error'}>{text}</Tag> },
  { title: 'Mobile', dataIndex: 'mobile', key: 'mobile' },
  { title: 'Desktop', dataIndex: 'desktop', key: 'desktop' },
];

// ── Main Dashboard Component ─────────────────────────────────────────────────
const Dashboard: React.FC = () => {
  const [activePage, setActivePage] = useState<string>('overview');
  const [loading] = useState(false); // can be true when fetching real data later

  const renderContent = () => {
    if (loading) return <Spin tip="Loading dashboard data..." size="large" style={{ margin: '200px auto', display: 'block' }} />;

    switch (activePage) {
      case 'overview':
        return (
          <>
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic title="Uptime (30 days)" value={99.94} precision={2} suffix="%" valueStyle={{ color: '#3f8600' }} />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic title="Avg Response Time" value={1.12} precision={2} suffix="s" valueStyle={{ color: '#faad14' }} />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic title="Error Rate" value={0.92} precision={2} suffix="%" valueStyle={{ color: '#cf1322' }} />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic title="Monitored Sites" value={7} valueStyle={{ color: '#1890ff' }} />
                </Card>
              </Col>
            </Row>

            <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
              <Col span={24}>
                <Card title="Performance Trend (Last 24h)">
                  <Line
                    data={mockTrendData}
                    xField="time"
                    yField="responseTime"
                    seriesField="errorRate" // optional second line
                    height={300}
                    smooth
                  />
                </Card>
              </Col>
            </Row>

            <Card title="Recent Issues" style={{ marginTop: 24 }}>
              <List
                dataSource={mockIssues}
                renderItem={(item) => (
                  <List.Item>
                    <Tag color={item.severity === 'Critical' ? 'error' : item.severity === 'Warning' ? 'warning' : 'blue'}>
                      {item.severity}
                    </Tag>
                    {item.message} • {item.time}
                  </List.Item>
                )}
              />
            </Card>
          </>
        );

      case 'core-vitals':
        return (
          <Card title="Core Web Vitals (Real User Data – P75)">
            <Table dataSource={mockVitals} columns={vitalsColumns} pagination={false} />
          </Card>
        );

      case 'page-speed':
        return (
          <Card title="Page Load & Speed">
            <Empty description="Top 10 slowest pages (sample placeholder)" />
            {/* Add table/chart later */}
          </Card>
        );

      case 'api-latency':
        return (
          <Card title="API / Endpoint Latency">
            <Empty description="P95 latency by endpoint (placeholder)" />
          </Card>
        );

      case 'errors':
        return (
          <Card title="Errors & Exceptions">
            <Table dataSource={mockErrors} columns={errorColumns} pagination={{ pageSize: 10 }} />
          </Card>
        );

      case 'uptime':
        return (
          <Card title="Uptime & Synthetic Monitoring">
            <Table dataSource={mockUptime} columns={uptimeColumns} pagination={false} />
          </Card>
        );

      case 'rum':
        return (
          <Card title="Real User Monitoring (RUM)">
            <Row gutter={16}>
              <Col span={12}><Card><Text strong>Geo Distribution</Text><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} /></Card></Col>
              <Col span={12}><Card><Text strong>Device Breakdown</Text><Empty image={Empty.PRESENTED_IMAGE_SIMPLE} /></Card></Col>
            </Row>
          </Card>
        );

      case 'alerts':
        return (
          <Card title="Alerts & Incidents">
            <Empty description="Recent alerts and notification history (placeholder)" />
          </Card>
        );

      default:
        return <Empty description="Select a section from the menu" />;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220} theme="light" collapsible={false}>
        <div style={{ height: 64, background: '#001529', color: 'white', textAlign: 'center', lineHeight: '64px', fontSize: 18 }}>
          Monitoring Dashboard
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[activePage]}
          onClick={({ key }) => setActivePage(key)}
          defaultOpenKeys={['performance']}
          style={{ height: 'calc(100vh - 64px)', borderRight: 0 }}
        >
          <Menu.Item key="overview" icon={<DashboardOutlined />}>
            Overview
          </Menu.Item>

          <Menu.SubMenu key="performance" icon={<LineChartOutlined />} title="Performance">
            <Menu.Item key="core-vitals" icon={<GlobalOutlined />}>Core Web Vitals</Menu.Item>
            <Menu.Item key="page-speed" icon={<MobileOutlined />}>Page Speed</Menu.Item>
            <Menu.Item key="api-latency" icon={<ApiOutlined />}>API Latency</Menu.Item>
          </Menu.SubMenu>

          <Menu.Item key="errors" icon={<WarningOutlined />}>
            Errors & Exceptions
          </Menu.Item>

          <Menu.Item key="uptime" icon={<ClockCircleOutlined />}>
            Uptime & Synthetic
          </Menu.Item>

          <Menu.Item key="rum" icon={<UserOutlined />}>
            Real User Monitoring
          </Menu.Item>

          <Menu.Item key="alerts" icon={<BellOutlined />}>
            Alerts & Incidents
          </Menu.Item>
        </Menu>
      </Sider>

      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Title level={3} style={{ margin: '16px 0' }}>
            {activePage === 'overview' ? 'Dashboard Overview' :
             activePage === 'core-vitals' ? 'Core Web Vitals' :
             activePage === 'page-speed' ? 'Page Load Performance' :
             activePage === 'api-latency' ? 'API Latency' :
             activePage === 'errors' ? 'Errors & Exceptions' :
             activePage === 'uptime' ? 'Uptime Monitoring' :
             activePage === 'rum' ? 'Real User Monitoring' :
             activePage === 'alerts' ? 'Alerts & Incidents' : 'Monitoring Dashboard'}
          </Title>
        </Header>

        <Content style={{ padding: '24px', background: '#f0f2f5' }}>
          {renderContent()}

          <Alert
            message="Beta Version – Sample Data Only"
            description="All numbers and charts are mock data. Real monitoring integration in progress."
            type="info"
            showIcon
            style={{ marginTop: 32 }}
          />
        </Content>
      </Layout>
    </Layout>
  );
};

export default Dashboard;