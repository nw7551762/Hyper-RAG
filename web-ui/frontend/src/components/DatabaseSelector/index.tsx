import React, { useEffect } from 'react';
import { Select, Typography, Space, Button, message, Spin, Popconfirm } from 'antd';
import type { SizeType } from 'antd/es/config-provider/SizeContext';
import { observer } from 'mobx-react';
import { DatabaseOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons';
import { storeGlobalUser } from '../../store/globalUser';
import { useTranslation } from 'react-i18next';

const { Text } = Typography;
const { Option } = Select;

interface DatabaseSelectorProps {
  /** 显示模式：选择器/按钮组/紧凑模式 */
  mode?: 'select' | 'buttons' | 'compact';
  /** 是否显示当前数据库信息 */
  showCurrent?: boolean;
  /** 是否显示刷新按钮 */
  showRefresh?: boolean;
  /** 是否显示删除按钮 */
  showDelete?: boolean;
  /** 选择器占位文本 */
  placeholder?: string;
  /** 自定义样式 */
  style?: React.CSSProperties;
  /** 组件大小 */
  size?: SizeType;
  /** 数据库变更回调 */
  onChange?: (value: string) => void;
  /** 是否禁用 */
  disabled?: boolean;
}

/**
 * 数据库选择组件
 */
export const DatabaseSelector: React.FC<DatabaseSelectorProps> = ({
    mode = 'select',
    showCurrent = true,
    showRefresh = false,
    showDelete = false,
    placeholder,
    style = {},
    size = 'middle',
    onChange,
    disabled = false
}) => {
    const { t } = useTranslation();
    
    // 如果没有提供placeholder，使用默认的国际化文本
    const defaultPlaceholder = placeholder || t('database.select_database_placeholder');

    // 初始化数据库列表
    useEffect(() => {
        if (!storeGlobalUser.selectedDatabase) {
            storeGlobalUser.restoreSelectedDatabase();
        }
        if (storeGlobalUser.availableDatabases.length === 0) {
            storeGlobalUser.loadDatabases();
        }
    }, []);

    // 处理数据库变更
    const handleDatabaseChange = (value) => {
        storeGlobalUser.setSelectedDatabase(value);
        onChange?.(value);
    };

    // 刷新数据库列表
    const handleRefresh = async () => {
        try {
            await storeGlobalUser.loadDatabases();
            message.success(t('database.refresh_success'));
        } catch (error) {
            message.error(t('database.refresh_failed'));
        }
    };

    // 删除数据库
    const handleDelete = async (databaseName: string) => {
        const success = await storeGlobalUser.deleteDatabase(databaseName);
        if (success) {
            message.success(t('database.delete_success'));
        } else {
            message.error(t('database.delete_failed'));
        }
    };

    // 选择器模式
    const renderSelectMode = () => (
        <Space size="middle" style={style}>
            <Select
                value={storeGlobalUser.selectedDatabase}
                onChange={handleDatabaseChange}
                style={{ minWidth: 250 }}
                placeholder={placeholder}
                size={size}
                disabled={disabled}
                loading={storeGlobalUser.availableDatabases.length === 0}
                dropdownRender={(menu) => (
                    <div>
                        {menu}
                        {showRefresh && (
                            <div style={{ padding: '8px', borderTop: '1px solid #f0f0f0' }}>
                                <Button
                                    type="text"
                                    size="small"
                                    icon={<ReloadOutlined />}
                                    onClick={handleRefresh}
                                    style={{ width: '100%' }}
                                >
                                    {t('database.refresh_list')}
                                </Button>
                            </div>
                        )}
                    </div>
                )}
            >
                {storeGlobalUser.availableDatabases.map((db) => (
                    <Option key={db.name} value={db.name}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center' }}>
                                <DatabaseOutlined style={{ marginRight: 6, color: '#1890ff' }} />
                                {db.description}
                            </div>
                            {showDelete && (
                                <Popconfirm
                                    title={`${t('database.confirm_delete_db')} "${db.name}"?`}
                                    onConfirm={(e) => {
                                        e.stopPropagation();
                                        handleDelete(db.name);
                                    }}
                                    onCancel={(e) => e.stopPropagation()}
                                    okText={t('database.confirm')}
                                    cancelText={t('database.cancel')}
                                >
                                    <Button
                                        type="text"
                                        danger
                                        size="small"
                                        icon={<DeleteOutlined />}
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                </Popconfirm>
                            )}
                        </div>
                    </Option>
                ))}
            </Select>

            {showRefresh && (
                <Button
                    type="text"
                    size={size}
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    disabled={disabled}
                />
            )}
        </Space>
    );

    // 按钮组模式
    const renderButtonsMode = () => (
        <Space size="small" style={style}>
            {storeGlobalUser.availableDatabases.map((db) => (
                <Button
                    key={db.name}
                    size={size}
                    type={storeGlobalUser.selectedDatabase === db.name ? 'primary' : 'default'}
                    onClick={() => handleDatabaseChange(db.name)}
                    disabled={disabled}
                    icon={<DatabaseOutlined />}
                    title={db.description}
                    style={{
                        borderColor: storeGlobalUser.selectedDatabase === db.name ? '#1890ff' : undefined,
                        borderRadius: '0.5rem'
                    }}
                    className='py-5 px-3'
                >
                    {db.description.replace('超图', '')}
                </Button>
            ))}
            {showRefresh && (
                <Button
                    type="text"
                    size={size}
                    icon={<ReloadOutlined />}
                    onClick={handleRefresh}
                    disabled={disabled}
                />
            )}
        </Space>
    );

    // 紧凑模式
    const renderCompactMode = () => (
        <Space size="small" style={style}>
            <Select
                value={storeGlobalUser.selectedDatabase}
                onChange={handleDatabaseChange}
                style={{ minWidth: 180 }}
                size={size}
                disabled={disabled}
                // bordered={false}
                placeholder={placeholder}
            >
                {storeGlobalUser.availableDatabases.map((db) => (
                    <Option key={db.name} value={db.name} title={db.description}>
                        <DatabaseOutlined style={{ marginRight: 6, color: '#1890ff' }} />
                        {db.description}
                    </Option>
                ))}
            </Select>
        </Space>
    );

    // 加载状态
    if (storeGlobalUser.availableDatabases.length === 0) {
        return (
            <Space style={style}>
                <Spin size="small" />
                <Text type="secondary">加载数据库列表...</Text>
            </Space>
        );
    }

    // 根据模式渲染不同的UI
    switch (mode) {
        case 'buttons':
            return renderButtonsMode();
        case 'compact':
            return renderCompactMode();
        case 'select':
        default:
            return renderSelectMode();
    }
};