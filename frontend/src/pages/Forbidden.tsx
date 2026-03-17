import { Result, Button } from 'antd';
import { useNavigate } from 'react-router-dom';
import { LockOutlined } from '@ant-design/icons';

const Forbidden = () => {
  const navigate = useNavigate();

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg-primary)',
      }}
    >
      <Result
        icon={<LockOutlined style={{ color: 'var(--error-color)', fontSize: 80 }} />}
        status="403"
        title={<span style={{ color: 'var(--text-primary)' }}>403 无访问权限</span>}
        subTitle={
          <span style={{ color: 'var(--text-secondary)' }}>
            抱歉，您没有权限访问此页面，请联系管理员获取权限
          </span>
        }
        extra={
          <Button type="primary" onClick={() => navigate('/')}>
            返回首页
          </Button>
        }
      />
    </div>
  );
};

export default Forbidden;
