"""Add asset config tables

Revision ID: add_asset_config_tables
Revises:
Create Date: 2024-01-20 10:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "add_asset_config_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create asset_configs table
    op.create_table(
        "asset_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "A_SHARE",
                "US_STOCK",
                "HK_STOCK",
                "CRYPTO",
                "FUTURES",
                "OPTIONS",
                "BONDS",
                "FUNDS",
                name="assettype",
            ),
            nullable=False,
        ),
        sa.Column(
            "name", sa.String(length=100), nullable=False, comment="资产类型名称"
        ),
        sa.Column(
            "display_name", sa.String(length=100), nullable=False, comment="显示名称"
        ),
        sa.Column("description", sa.Text(), nullable=True, comment="资产类型描述"),
        sa.Column(
            "supported_functions", sa.JSON(), nullable=False, comment="支持的功能列表"
        ),
        sa.Column("screener_config", sa.JSON(), nullable=True, comment="筛选器配置"),
        sa.Column("backtest_config", sa.JSON(), nullable=True, comment="回测配置"),
        sa.Column("data_source_config", sa.JSON(), nullable=True, comment="数据源配置"),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "INACTIVE", "MAINTENANCE", name="assetconfigstatus"),
            nullable=False,
        ),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, comment="是否启用"),
        sa.Column("sort_order", sa.Integer(), nullable=True, comment="排序顺序"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_configs_asset_type"),
        "asset_configs",
        ["asset_type"],
        unique=True,
    )
    op.create_index(op.f("ix_asset_configs_id"), "asset_configs", ["id"], unique=False)

    # Create asset_symbols table
    op.create_table(
        "asset_symbols",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "A_SHARE",
                "US_STOCK",
                "HK_STOCK",
                "CRYPTO",
                "FUTURES",
                "OPTIONS",
                "BONDS",
                "FUNDS",
                name="assettype",
            ),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=50), nullable=False, comment="标的代码"),
        sa.Column("name", sa.String(length=200), nullable=False, comment="标的名称"),
        sa.Column(
            "full_name", sa.String(length=500), nullable=True, comment="完整名称"
        ),
        sa.Column("exchange", sa.String(length=50), nullable=True, comment="交易所"),
        sa.Column("sector", sa.String(length=100), nullable=True, comment="行业/板块"),
        sa.Column("industry", sa.String(length=100), nullable=True, comment="细分行业"),
        sa.Column("market_cap", sa.String(length=50), nullable=True, comment="市值"),
        sa.Column("currency", sa.String(length=10), nullable=True, comment="交易货币"),
        sa.Column("lot_size", sa.Integer(), nullable=True, comment="最小交易单位"),
        sa.Column(
            "tick_size", sa.String(length=20), nullable=True, comment="最小价格变动单位"
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, comment="是否活跃"),
        sa.Column("is_tradable", sa.Boolean(), nullable=False, comment="是否可交易"),
        sa.Column(
            "listing_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="上市日期",
        ),
        sa.Column(
            "delisting_date",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="退市日期",
        ),
        sa.Column("metadata", sa.JSON(), nullable=True, comment="扩展元数据"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_symbols_asset_type"),
        "asset_symbols",
        ["asset_type"],
        unique=False,
    )
    op.create_index(op.f("ix_asset_symbols_id"), "asset_symbols", ["id"], unique=False)
    op.create_index(
        op.f("ix_asset_symbols_symbol"), "asset_symbols", ["symbol"], unique=False
    )

    # Create asset_market_data table
    op.create_table(
        "asset_market_data",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "A_SHARE",
                "US_STOCK",
                "HK_STOCK",
                "CRYPTO",
                "FUTURES",
                "OPTIONS",
                "BONDS",
                "FUNDS",
                name="assettype",
            ),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("open_price", sa.String(length=20), nullable=True, comment="开盘价"),
        sa.Column("high_price", sa.String(length=20), nullable=True, comment="最高价"),
        sa.Column("low_price", sa.String(length=20), nullable=True, comment="最低价"),
        sa.Column("close_price", sa.String(length=20), nullable=True, comment="收盘价"),
        sa.Column("volume", sa.String(length=30), nullable=True, comment="成交量"),
        sa.Column("turnover", sa.String(length=30), nullable=True, comment="成交额"),
        sa.Column(
            "change_amount", sa.String(length=20), nullable=True, comment="涨跌额"
        ),
        sa.Column(
            "change_percent", sa.String(length=10), nullable=True, comment="涨跌幅"
        ),
        sa.Column("amplitude", sa.String(length=10), nullable=True, comment="振幅"),
        sa.Column("ma5", sa.String(length=20), nullable=True, comment="5日均线"),
        sa.Column("ma10", sa.String(length=20), nullable=True, comment="10日均线"),
        sa.Column("ma20", sa.String(length=20), nullable=True, comment="20日均线"),
        sa.Column("ma60", sa.String(length=20), nullable=True, comment="60日均线"),
        sa.Column("pe_ratio", sa.String(length=10), nullable=True, comment="市盈率"),
        sa.Column("pb_ratio", sa.String(length=10), nullable=True, comment="市净率"),
        sa.Column("ps_ratio", sa.String(length=10), nullable=True, comment="市销率"),
        sa.Column(
            "dividend_yield", sa.String(length=10), nullable=True, comment="股息率"
        ),
        sa.Column(
            "open_interest", sa.String(length=30), nullable=True, comment="持仓量"
        ),
        sa.Column(
            "settlement_price", sa.String(length=20), nullable=True, comment="结算价"
        ),
        sa.Column(
            "implied_volatility",
            sa.String(length=10),
            nullable=True,
            comment="隐含波动率",
        ),
        sa.Column("market_cap_rank", sa.Integer(), nullable=True, comment="市值排名"),
        sa.Column(
            "circulating_supply",
            sa.String(length=30),
            nullable=True,
            comment="流通供应量",
        ),
        sa.Column(
            "total_supply", sa.String(length=30), nullable=True, comment="总供应量"
        ),
        sa.Column(
            "trade_date", sa.DateTime(timezone=True), nullable=False, comment="交易日期"
        ),
        sa.Column(
            "data_timestamp",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="数据时间戳",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_market_data_asset_type"),
        "asset_market_data",
        ["asset_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_market_data_id"), "asset_market_data", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_asset_market_data_symbol"),
        "asset_market_data",
        ["symbol"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_market_data_trade_date"),
        "asset_market_data",
        ["trade_date"],
        unique=False,
    )

    # Create asset_screener_templates table
    op.create_table(
        "asset_screener_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "A_SHARE",
                "US_STOCK",
                "HK_STOCK",
                "CRYPTO",
                "FUTURES",
                "OPTIONS",
                "BONDS",
                "FUNDS",
                name="assettype",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False, comment="模板名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="模板描述"),
        sa.Column("criteria", sa.JSON(), nullable=False, comment="筛选条件配置"),
        sa.Column("is_public", sa.Boolean(), nullable=True, comment="是否公开模板"),
        sa.Column("is_system", sa.Boolean(), nullable=True, comment="是否系统模板"),
        sa.Column("usage_count", sa.Integer(), nullable=True, comment="使用次数"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建者ID"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_screener_templates_asset_type"),
        "asset_screener_templates",
        ["asset_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_screener_templates_id"),
        "asset_screener_templates",
        ["id"],
        unique=False,
    )

    # Create asset_backtest_templates table
    op.create_table(
        "asset_backtest_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "asset_type",
            sa.Enum(
                "A_SHARE",
                "US_STOCK",
                "HK_STOCK",
                "CRYPTO",
                "FUTURES",
                "OPTIONS",
                "BONDS",
                "FUNDS",
                name="assettype",
            ),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False, comment="模板名称"),
        sa.Column("description", sa.Text(), nullable=True, comment="模板描述"),
        sa.Column(
            "strategy_type", sa.String(length=50), nullable=False, comment="策略类型"
        ),
        sa.Column("strategy_config", sa.JSON(), nullable=False, comment="策略配置"),
        sa.Column("backtest_config", sa.JSON(), nullable=True, comment="回测配置"),
        sa.Column("is_public", sa.Boolean(), nullable=True, comment="是否公开模板"),
        sa.Column("is_system", sa.Boolean(), nullable=True, comment="是否系统模板"),
        sa.Column("usage_count", sa.Integer(), nullable=True, comment="使用次数"),
        sa.Column("created_by", sa.Integer(), nullable=True, comment="创建者ID"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_asset_backtest_templates_asset_type"),
        "asset_backtest_templates",
        ["asset_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_asset_backtest_templates_id"),
        "asset_backtest_templates",
        ["id"],
        unique=False,
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_index(
        op.f("ix_asset_backtest_templates_id"), table_name="asset_backtest_templates"
    )
    op.drop_index(
        op.f("ix_asset_backtest_templates_asset_type"),
        table_name="asset_backtest_templates",
    )
    op.drop_table("asset_backtest_templates")

    op.drop_index(
        op.f("ix_asset_screener_templates_id"), table_name="asset_screener_templates"
    )
    op.drop_index(
        op.f("ix_asset_screener_templates_asset_type"),
        table_name="asset_screener_templates",
    )
    op.drop_table("asset_screener_templates")

    op.drop_index(
        op.f("ix_asset_market_data_trade_date"), table_name="asset_market_data"
    )
    op.drop_index(op.f("ix_asset_market_data_symbol"), table_name="asset_market_data")
    op.drop_index(op.f("ix_asset_market_data_id"), table_name="asset_market_data")
    op.drop_index(
        op.f("ix_asset_market_data_asset_type"), table_name="asset_market_data"
    )
    op.drop_table("asset_market_data")

    op.drop_index(op.f("ix_asset_symbols_symbol"), table_name="asset_symbols")
    op.drop_index(op.f("ix_asset_symbols_id"), table_name="asset_symbols")
    op.drop_index(op.f("ix_asset_symbols_asset_type"), table_name="asset_symbols")
    op.drop_table("asset_symbols")

    op.drop_index(op.f("ix_asset_configs_id"), table_name="asset_configs")
    op.drop_index(op.f("ix_asset_configs_asset_type"), table_name="asset_configs")
    op.drop_table("asset_configs")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS assetconfigstatus")
    op.execute("DROP TYPE IF EXISTS assettype")
