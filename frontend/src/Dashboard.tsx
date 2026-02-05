// src/Dashboard.tsx
import React, { useState, useEffect } from 'react';
import {
  Layout, Menu, Card, Statistic, Row, Col, Table, Typography, Spin, Alert, List, Tag, Empty, message, Button,
} from 'antd';
import {
  DashboardOutlined, ApiOutlined, WarningOutlined, BarChartOutlined,
  ReloadOutlined, CheckCircleOutlined, UserOutlined,
} from '@ant-design/icons';
import { Column, Pie } from '@ant-design/plots';
import type { ColumnsType } from 'antd/es/table';

const { Header, Content, Sider } = Layout;
const { Title, Text } = Typography;

// ══════════════════════════════════════════════════════════════════════
// API Configuration
// ══════════════════════════════════════════════════════════════════════

const API_BASE_URL = 'http://localhost:8002/api';

// ══════════════════════════════════════════════════════════════════════
// TypeScript Interfaces
// ══════════════════════════════════════════════════════════════════════

interface Metrics {
  total_requests: number;
  error_count: number;
  error_rate: number;
  avg_response_time: number;
  p50_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
  requests_by_status: Record<string, number>;
  requests_by_method: Record<string, number>;
  unique_users: number;
  authenticated_requests: number;
}

interface EndpointStat {
  path: string;
  count: number;
  errors: number;
  avg_response_time: number;
  p95_response_time: number;
  error_rate: number;
}

interface ErrorLog {
  timestamp: string;
  level: string;
  method?: string;
  path?: string;
  status_code?: number;
  duration_ms?: number;
  error_type?: string;
  error_message?: string;
  user_id?: number;
}

interface HealthStatus {
  status: string;
  log_file: {
    exists: boolean;
    path: string;
    size_bytes: number;
    total_lines: number;
  };
}

// ══════════════════════════════════════════════════════════════════════
// Main Dashboard Component
// ══════════════════════════════════════════════════════════════════════

const Dashboard: React.FC = () => {
  const [activePage, setActivePage] = useState<string>('overview');
  const [loading, setLoading] = useState(false);
  const [timeWindow, setTimeWindow] = useState(60); // minutes
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  // State for data
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [endpoints, setEndpoints] = useState<EndpointStat[]>([]);
  const [errors, setErrors] = useState<ErrorLog[]>([]);
  const [trafficData, setTrafficData] = useState<any[]>([]);
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);

  // ──────────────────────────────────────────────────────────────────
  // API Calls
  // ──────────────────────────────────────────────────────────────────

  const fetchHealth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      const data = await response.json();
      setHealthStatus(data);
    } catch (error) {
      console.error('Health check failed:', error);
    }
  };

  const fetchMetrics = async (minutes: number = 60) => {
    try {
      const response = await fetch(`${API_BASE_URL}/metrics?minutes=${minutes}`);
      const data = await response.json();
      setMetrics(data.metrics);
    } catch (error) {
      message.error('Failed to fetch metrics');
      console.error(error);
    }
  };

  const fetchEndpoints = async (minutes: number = 60) => {
    try {
      const response = await fetch(`${API_BASE_URL}/endpoints?minutes=${minutes}&limit=10`);
      const data = await response.json();
      setEndpoints(data.endpoints);
    } catch (error) {
      message.error('Failed to fetch endpoint stats');
      console.error(error);
    }
  };

  const fetchErrors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/errors?limit=20`);
      const data = await response.json();
      setErrors(data.errors);
    } catch (error) {
      message.error('Failed to fetch errors');
      console.error(error);
    }
  };

  const fetchTraffic = async (minutes: number = 1440) => {
    try {
      const response = await fetch(`${API_BASE_URL}/traffic?minutes=${minutes}`);
      const data = await response.json();
      
      // Convert to chart format
      const chartData = Object.entries(data.hourly_distribution).map(([hour, count]) => ({
        hour,
        requests: count as number,
      }));
      
      setTrafficData(chartData);
    } catch (error) {
      message.error('Failed to fetch traffic data');
      console.error(error);
    }
  };

  // ──────────────────────────────────────────────────────────────────
  // Load Data
  // ──────────────────────────────────────────────────────────────────

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchHealth(),
        fetchMetrics(timeWindow),
        fetchEndpoints(timeWindow),
        fetchErrors(),
        fetchTraffic(1440), // Last 24 hours
      ]);
      message.success('Dashboard updated', 1);
    } catch (error) {
      message.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, [timeWindow]);

  useEffect(() => {
    if (!autoRefresh) return;
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, timeWindow]);

  // ──────────────────────────────────────────────────────────────────
  // Table Columns
  // ──────────────────────────────────────────────────────────────────

  const endpointColumns: ColumnsType<EndpointStat> = [
    { 
      title: 'Endpoint', 
      dataIndex: 'path', 
      key: 'path', 
      ellipsis: true,
      width: '35%',
    },
    { 
      title: 'Requests', 
      dataIndex: 'count', 
      key: 'count', 
      sorter: (a, b) => a.count - b.count,
      width: '13%',
    },
    { 
      title: 'Errors', 
      dataIndex: 'errors', 
      key: 'errors', 
      sorter: (a, b) => a.errors - b.errors,
      width: '13%',
    },
    { 
      title: 'Avg (ms)', 
      dataIndex: 'avg_response_time', 
      key: 'avg_response_time', 
      sorter: (a, b) => a.avg_response_time - b.avg_response_time,
      render: (time: number) => time.toFixed(2),
      width: '13%',
    },
    { 
      title: 'P95 (ms)', 
      dataIndex: 'p95_response_time', 
      key: 'p95_response_time', 
      sorter: (a, b) => a.p95_response_time - b.p95_response_time,
      render: (time: number) => time.toFixed(2),
      width: '13%',
    },
    { 
      title: 'Error Rate', 
      dataIndex: 'error_rate', 
      key: 'error_rate',
      render: (rate: number) => (
        <Tag color={rate > 5 ? 'red' : rate > 1 ? 'orange' : 'green'}>
          {rate.toFixed(2)}%
        </Tag>
      ),
      sorter: (a, b) => a.error_rate - b.error_rate,
      width: '13%',
    },
  ];

  const errorColumns: ColumnsType<ErrorLog> = [
    { 
      title: 'Time', 
      dataIndex: 'timestamp', 
      key: 'timestamp',
      render: (ts: string) => new Date(ts).toLocaleString(),
      width: 180,
    },
    { 
      title: 'Method', 
      dataIndex: 'method', 
      key: 'method', 
      width: 80 
    },
    { 
      title: 'Path', 
      dataIndex: 'path', 
      key: 'path', 
      ellipsis: true 
    },
    { 
      title: 'Status', 
      dataIndex: 'status_code', 
      key: 'status_code',
      render: (status?: number) => status ? (
        <Tag color={status >= 500 ? 'red' : 'orange'}>{status}</Tag>
      ) : '-',
      width: 80,
    },
    { 
      title: 'Error', 
      dataIndex: 'error_message', 
      key: 'error_message',
      ellipsis: true,
      render: (msg?: string, record?: ErrorLog) => msg || record?.error_type || '-',
    },
  ];

  // ──────────────────────────────────────────────────────────────────
  // Render Content by Active Page
  // ──────────────────────────────────────────────────────────────────

  const renderContent = () => {
    if (loading && !metrics) {
      return (
        <div style={{ textAlign: 'center', padding: '100px' }}>
          <Spin tip="Loading dashboard data..." size="large" />
        </div>
      );
    }

    switch (activePage) {
      case 'overview':
        return (
          <>
            {/* System Health */}
            {healthStatus && !healthStatus.log_file.exists && (
              <Alert
                message="Log File Not Found"
                description={`Cannot find monitoring log at: ${healthStatus.log_file.path}. Make sure Django is running and logging is configured.`}
                type="error"
                showIcon
                style={{ marginBottom: 24 }}
              />
            )}

            {/* Top Stats */}
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="Total Requests" 
                    value={metrics?.total_requests || 0}
                    valueStyle={{ color: '#1890ff' }}
                    prefix={<CheckCircleOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="Avg Response Time" 
                    value={metrics?.avg_response_time || 0}
                    precision={2}
                    suffix="ms"
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="Error Rate" 
                    value={metrics?.error_rate || 0}
                    precision={2}
                    suffix="%"
                    valueStyle={{ 
                      color: (metrics?.error_rate || 0) > 5 ? '#cf1322' : 
                             (metrics?.error_rate || 0) > 1 ? '#faad14' : '#52c41a'
                    }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="P95 Latency" 
                    value={metrics?.p95_response_time || 0}
                    precision={2}
                    suffix="ms"
                    valueStyle={{ color: '#722ed1' }}
                  />
                </Card>
              </Col>
            </Row>

            {/* Additional Metrics */}
            <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="Unique Users" 
                    value={metrics?.unique_users || 0}
                    prefix={<UserOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="Authenticated Requests" 
                    value={metrics?.authenticated_requests || 0}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="P50 Latency" 
                    value={metrics?.p50_response_time || 0}
                    precision={2}
                    suffix="ms"
                  />
                </Card>
              </Col>
              <Col xs={24} sm={12} lg={6}>
                <Card>
                  <Statistic 
                    title="P99 Latency" 
                    value={metrics?.p99_response_time || 0}
                    precision={2}
                    suffix="ms"
                  />
                </Card>
              </Col>
            </Row>

            {/* Charts */}
            <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
              <Col xs={24} lg={12}>
                <Card title="HTTP Status Codes Distribution">
                  {metrics?.requests_by_status && Object.keys(metrics.requests_by_status).length > 0 ? (
                    <Pie
                      data={Object.entries(metrics.requests_by_status).map(([status, count]) => ({
                        type: `${status}${Number(status) >= 400 ? ' (Error)' : ' (Success)'}`,
                        value: count,
                      }))}
                      angleField="value"
                      colorField="type"
                      radius={0.8}
                      label={{
                        type: 'outer',
                        content: '{name} {percentage}',
                      }}
                      height={300}
                      legend={{
                        position: 'bottom',
                      }}
                    />
                  ) : (
                    <Empty description="No data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </Card>
              </Col>

              <Col xs={24} lg={12}>
                <Card title="HTTP Methods Distribution">
                  {metrics?.requests_by_method && Object.keys(metrics.requests_by_method).length > 0 ? (
                    <Column
                      data={Object.entries(metrics.requests_by_method).map(([method, count]) => ({
                        method,
                        count,
                      }))}
                      xField="method"
                      yField="count"
                      label={{
                        position: 'top',
                        style: {
                          fill: '#000',
                          opacity: 0.6,
                        },
                      }}
                      height={300}
                      color="#1890ff"
                    />
                  ) : (
                    <Empty description="No data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                  )}
                </Card>
              </Col>
            </Row>

            {/* Recent Errors */}
            <Card title="Recent Errors" style={{ marginTop: 24 }}>
              {errors.length > 0 ? (
                <List
                  dataSource={errors.slice(0, 5)}
                  renderItem={(item) => (
                    <List.Item>
                      <div style={{ width: '100%' }}>
                        <div>
                          <Tag color={item.status_code && item.status_code >= 500 ? 'red' : 'orange'}>
                            {item.status_code || item.error_type || 'ERROR'}
                          </Tag>
                          <Text strong>{item.method} {item.path}</Text>
                          {item.user_id && (
                            <Tag color="blue" style={{ marginLeft: 8 }}>
                              User: {item.user_id}
                            </Tag>
                          )}
                        </div>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          {item.error_message || 'Unknown error'} • {new Date(item.timestamp).toLocaleString()}
                        </Text>
                      </div>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="No errors recorded" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </>
        );

      case 'api-performance':
        return (
          <>
            <Card 
              title="API Endpoint Performance"
              extra={
                <Text type="secondary">
                  Top 10 endpoints by request count
                </Text>
              }
            >
              {endpoints.length > 0 ? (
                <Table 
                  dataSource={endpoints.map((e, i) => ({ ...e, key: i }))} 
                  columns={endpointColumns} 
                  pagination={false}
                  scroll={{ x: 800 }}
                />
              ) : (
                <Empty description="No endpoint data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* Slowest Endpoints */}
            <Card title="Slowest Endpoints (by P95 Response Time)" style={{ marginTop: 24 }}>
              {endpoints.length > 0 ? (
                <List
                  dataSource={[...endpoints].sort((a, b) => b.p95_response_time - a.p95_response_time).slice(0, 5)}
                  renderItem={(item) => (
                    <List.Item>
                      <div style={{ width: '100%' }}>
                        <div>
                          <Text strong>{item.path}</Text>
                          <Tag color="orange" style={{ marginLeft: 8 }}>
                            P95: {item.p95_response_time.toFixed(2)}ms
                          </Tag>
                          <Tag color="blue">
                            Avg: {item.avg_response_time.toFixed(2)}ms
                          </Tag>
                        </div>
                        <Text type="secondary">
                          {item.count} requests • {item.errors} errors ({item.error_rate.toFixed(2)}% error rate)
                        </Text>
                      </div>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="No data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* Most Popular Endpoints */}
            <Card title="Most Popular Endpoints" style={{ marginTop: 24 }}>
              {endpoints.length > 0 ? (
                <List
                  dataSource={endpoints.slice(0, 5)}
                  renderItem={(item) => (
                    <List.Item>
                      <div style={{ width: '100%' }}>
                        <div>
                          <Text strong>{item.path}</Text>
                          <Tag color="blue" style={{ marginLeft: 8 }}>
                            {item.count} requests
                          </Tag>
                        </div>
                        <Text type="secondary">
                          Avg: {item.avg_response_time.toFixed(2)}ms • P95: {item.p95_response_time.toFixed(2)}ms • {item.error_rate.toFixed(2)}% errors
                        </Text>
                      </div>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="No data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </>
        );

      case 'errors':
        return (
          <Card title="Error Log" extra={<Text type="secondary">Last 20 errors</Text>}>
            {errors.length > 0 ? (
              <Table 
                dataSource={errors.map((e, i) => ({ ...e, key: i }))} 
                columns={errorColumns} 
                pagination={{ pageSize: 20 }}
                scroll={{ x: 800 }}
              />
            ) : (
              <Empty description="No errors recorded" image={Empty.PRESENTED_IMAGE_SIMPLE} />
            )}
          </Card>
        );

      case 'traffic':
        return (
          <>
            <Card title="Traffic Distribution (Last 24 Hours)">
              {trafficData.length > 0 ? (
                <Column
                  data={trafficData}
                  xField="hour"
                  yField="requests"
                  label={{
                    position: 'top',
                  }}
                  height={400}
                  color="#1890ff"
                />
              ) : (
                <Empty description="No traffic data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>

            {/* Peak Traffic Info */}
            {trafficData.length > 0 && (
              <Card title="Traffic Summary" style={{ marginTop: 24 }}>
                <Row gutter={16}>
                  <Col span={8}>
                    <Statistic 
                      title="Peak Hour" 
                      value={trafficData.reduce((max, item) => item.requests > max.requests ? item : max).hour}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic 
                      title="Peak Requests" 
                      value={Math.max(...trafficData.map(d => d.requests))}
                    />
                  </Col>
                  <Col span={8}>
                    <Statistic 
                      title="Total Requests (24h)" 
                      value={trafficData.reduce((sum, item) => sum + item.requests, 0)}
                    />
                  </Col>
                </Row>
              </Card>
            )}

            {/* Hourly Breakdown Table */}
            {trafficData.length > 0 && (
              <Card title="Hourly Breakdown" style={{ marginTop: 24 }}>
                <Table
                  dataSource={trafficData.map((item, i) => ({ ...item, key: i }))}
                  columns={[
                    { title: 'Hour', dataIndex: 'hour', key: 'hour' },
                    { 
                      title: 'Requests', 
                      dataIndex: 'requests', 
                      key: 'requests',
                      sorter: (a, b) => a.requests - b.requests,
                    },
                  ]}
                  pagination={false}
                  size="small"
                />
              </Card>
            )}
          </>
        );

      default:
        return <Empty description="Select a section from the menu" />;
    }
  };

  // ──────────────────────────────────────────────────────────────────
  // Main Render
  // ──────────────────────────────────────────────────────────────────

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sider width={220} theme="light" breakpoint="lg" collapsedWidth="0">
        <div style={{ 
          height: 64, 
          background: '#001529', 
          color: 'white', 
          textAlign: 'center', 
          lineHeight: '64px', 
          fontSize: 18,
          fontWeight: 'bold',
        }}>
          📊 Monitoring
        </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[activePage]}
          onClick={({ key }) => setActivePage(key)}
          style={{ height: 'calc(100vh - 64px)', borderRight: 0 }}
        >
          <Menu.Item key="overview" icon={<DashboardOutlined />}>
            Overview
          </Menu.Item>
          <Menu.Item key="api-performance" icon={<ApiOutlined />}>
            API Performance
          </Menu.Item>
          <Menu.Item key="errors" icon={<WarningOutlined />}>
            Errors & Exceptions
          </Menu.Item>
          <Menu.Item key="traffic" icon={<BarChartOutlined />}>
            Traffic Analysis
          </Menu.Item>
        </Menu>
      </Sider>

      {/* Main Layout */}
      <Layout>
        {/* Header */}
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px', 
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <Title level={3} style={{ margin: '16px 0' }}>
            {activePage === 'overview' ? 'Dashboard Overview' :
             activePage === 'api-performance' ? 'API Performance' :
             activePage === 'errors' ? 'Errors & Exceptions' :
             activePage === 'traffic' ? 'Traffic Analysis' : 'Monitoring Dashboard'}
          </Title>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Time Window Selector */}
            <div>
              <Text type="secondary" style={{ marginRight: 8 }}>Time Window:</Text>
              <select 
                value={timeWindow} 
                onChange={(e) => setTimeWindow(Number(e.target.value))}
                style={{ 
                  padding: '4px 8px', 
                  borderRadius: '4px', 
                  border: '1px solid #d9d9d9',
                  cursor: 'pointer',
                }}
              >
                <option value={15}>15 minutes</option>
                <option value={60}>1 hour</option>
                <option value={360}>6 hours</option>
                <option value={1440}>24 hours</option>
                <option value={10080}>7 days</option>
              </select>
            </div>

            {/* Auto-refresh Toggle */}
            <Button
              size="small"
              type={autoRefresh ? 'primary' : 'default'}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              {autoRefresh ? 'Auto-refresh: ON' : 'Auto-refresh: OFF'}
            </Button>

            {/* Manual Refresh */}
            <Button
              icon={<ReloadOutlined spin={loading} />}
              onClick={loadDashboardData}
              disabled={loading}
            >
              Refresh
            </Button>
          </div>
        </Header>

        {/* Content */}
        <Content style={{ padding: '24px', background: '#f0f2f5' }}>
          {renderContent()}

          {/* Footer Info */}
          <Alert
            message="Phase 1: Log-Based Monitoring"
            description={
              <div>
                <div>All metrics are calculated from backend logs (monitoring.jsonl).</div>
                <div>Data auto-refreshes every 30 seconds when enabled.</div>
                {healthStatus && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="secondary">
                      Log file: {healthStatus.log_file.exists ? '✅ Found' : '❌ Not Found'} • 
                      {healthStatus.log_file.total_lines} entries • 
                      {(healthStatus.log_file.size_bytes / 1024).toFixed(2)} KB
                    </Text>
                  </div>
                )}
              </div>
            }
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