# Type stubs for SQLAlchemy models
from datetime import date, datetime

from sqlalchemy.ext.declarative import DeclarativeMeta

class Base(metaclass=DeclarativeMeta): ...

class StockData(Base):
    __tablename__: str
    id: int
    ts_code: str
    trade_date: date
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    pre_close: float | None
    change: float | None
    pct_chg: float | None
    vol: float | None
    amount: float | None
    interval: str

class StockInfo(Base):
    __tablename__: str
    ts_code: str
    name: str
    market_type: str
    last_updated: datetime

class DailyStockMetrics(Base):
    __tablename__: str
    id: int
    code: str
    date: date
    market: str
    close_price: float | None
    pe_ratio: float | None
    pb_ratio: float | None
    market_cap: int | None
    dividend_yield: float | None
    ma5: float | None
    ma20: float | None
    volume: int | None
    updated_at: datetime

class AnnualEarnings(Base):
    __tablename__: str
    id: int
    ts_code: str
    ann_date: date
    f_ann_date: date
    end_date: date
    eps: float | None
    dt_eps: float | None
    total_revenue_ps: float | None
    revenue_ps: float | None
    capital_rese_ps: float | None
    surplus_rese_ps: float | None
    undist_profit_ps: float | None
    extra_item: float | None
    profit_dedt: float | None
    gross_margin: float | None
    current_ratio: float | None
    quick_ratio: float | None
    cash_ratio: float | None
    invturn_days: float | None
    arturn_days: float | None
    inv_turn: float | None
    ar_turn: float | None
    ca_turn: float | None
    fa_turn: float | None
    assets_turn: float | None
    op_income: float | None
    valuechange_income: float | None
    interst_income: float | None
    daa: float | None
    ebit: float | None
    ebitda: float | None
    fcff: float | None
    fcfe: float | None
    current_exint: float | None
    noncurrent_exint: float | None
    interestdebt: float | None
    netdebt: float | None
    tangible_asset: float | None
    working_capital: float | None
    networking_capital: float | None
    invest_capital: float | None
    retained_earnings: float | None
    diluted2_eps: float | None
    bps: float | None
    ocfps: float | None
    retainedps: float | None
    cfps: float | None
    ebit_ps: float | None
    fcff_ps: float | None
    fcfe_ps: float | None
    netprofit_margin: float | None
    grossprofit_margin: float | None
    cogs_of_sales: float | None
    expense_of_sales: float | None
    profit_to_gr: float | None
    saleexp_to_gr: float | None
    adminexp_of_gr: float | None
    finaexp_of_gr: float | None
    impai_ttm: float | None
    gc_of_gr: float | None
    op_of_gr: float | None
    ebit_of_gr: float | None
    roe: float | None
    roe_waa: float | None
    roe_dt: float | None
    roa: float | None
    npta: float | None
    roic: float | None
    roe_yearly: float | None
    roa2_yearly: float | None
    roe_avg: float | None
    opincome_of_ebt: float | None
    investincome_of_ebt: float | None
    n_op_profit_of_ebt: float | None
    tax_to_ebt: float | None
    dtprofit_to_profit: float | None
    salescash_to_or: float | None
    ocf_to_or: float | None
    ocf_to_opincome: float | None
    capitalized_to_da: float | None
    debt_to_assets: float | None
    assets_to_eqt: float | None
    dp_assets_to_eqt: float | None
    ca_to_assets: float | None
    nca_to_assets: float | None
    tbassets_to_totalassets: float | None
    int_to_talcap: float | None
    eqt_to_talcapital: float | None
    currentdebt_to_debt: float | None
    longdeb_to_debt: float | None
    ocf_to_shortdebt: float | None
    debt_to_eqt: float | None
    eqt_to_debt: float | None
    eqt_to_interestdebt: float | None
    tangibleasset_to_debt: float | None
    tangasset_to_intdebt: float | None
    tangibleasset_to_netdebt: float | None
    ocf_to_debt: float | None
    ocf_to_interestdebt: float | None
    ocf_to_netdebt: float | None
    ebit_to_interest: float | None
    longdebt_to_workingcapital: float | None
    ebitda_to_debt: float | None
    turn_days: float | None
    roa_yearly: float | None
    roa_dp: float | None
    fixed_assets: float | None
    profit_prefin_exp: float | None
    non_op_profit: float | None
    op_profit: float | None
    ebit_ebitda: float | None
    profit_to_op: float | None
    q_opincome: float | None
    q_investincome: float | None
    q_dtprofit: float | None
    q_eps: float | None
    q_netprofit_margin: float | None
    q_gsprofit_margin: float | None
    q_exp_to_sales: float | None
    q_profit_to_gr: float | None
    q_saleexp_to_gr: float | None
    q_adminexp_to_gr: float | None
    q_finaexp_to_gr: float | None
    q_impair_to_gr_ttm: float | None
    q_gc_to_gr: float | None
    q_op_to_gr: float | None
    q_roe: float | None
    q_dt_roe: float | None
    q_npta: float | None
    q_opincome_to_ebt: float | None
    q_investincome_to_ebt: float | None
    q_dtprofit_to_profit: float | None
    q_salescash_to_or: float | None
    q_ocf_to_sales: float | None
    q_ocf_to_or: float | None
    basic_eps_yoy: float | None
    dt_eps_yoy: float | None
    cfps_yoy: float | None
    op_yoy: float | None
    ebt_yoy: float | None
    netprofit_yoy: float | None
    dt_netprofit_yoy: float | None
    ocf_yoy: float | None
    roe_yoy: float | None
    bps_yoy: float | None
    assets_yoy: float | None
    eqt_yoy: float | None
    tr_yoy: float | None
    or_yoy: float | None
    q_gr_yoy: float | None
    q_gr_qoq: float | None
    q_sales_yoy: float | None
    q_sales_qoq: float | None
    q_op_yoy: float | None
    q_op_qoq: float | None
    q_profit_yoy: float | None
    q_profit_qoq: float | None
    q_netprofit_yoy: float | None
    q_netprofit_qoq: float | None
    equity_yoy: float | None
    rd_exp: float | None
    update_flag: str | None

class CorporateAction(Base):
    __tablename__: str
    id: int
    ts_code: str
    ann_date: date
    record_date: date | None
    ex_date: date | None
    pay_date: date | None
    div_proc: str | None
    stk_div: float | None
    stk_bo_rate: float | None
    stk_co_rate: float | None
    cash_div: float | None
    cash_div_tax: float | None
    record_date_desc: str | None
    ex_date_desc: str | None
    pay_date_desc: str | None
    base_date: date | None
    base_share: float | None

class FundamentalData(Base):
    __tablename__: str
    id: int
    ts_code: str
    trade_date: date
    pe_ratio: float | None
    pb_ratio: float | None
    market_cap: float | None
    total_share: float | None
    float_share: float | None
    free_share: float | None
    turnover_rate: float | None
    turnover_rate_f: float | None
    volume_ratio: float | None
    pe_ttm: float | None
    pb_mrq: float | None
    ps_ttm: float | None
    ps_mrq: float | None
    dv_ratio: float | None
    dv_ttm: float | None
    total_mv: float | None
    circ_mv: float | None

class IndustryClassification(Base):
    __tablename__: str
    ts_code: str
    industry_code: str
    industry_name: str
    src: str
    level: str
    industry_code_new: str | None
    industry_name_new: str | None

class DataQualityLog(Base):
    __tablename__: str
    id: int
    record_id: int
    table_name: str
    operation_type: str
    status: str
    message: str | None
    error_details: str | None
    execution_time: float | None
    created_at: datetime

class User(Base):
    __tablename__: str
    id: int
    username: str
    email: str
    phone: str | None
    password_hash: str
    full_name: str | None
    avatar_url: str | None
    is_active: bool
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None

class UserRole(Base):
    __tablename__: str
    id: int
    name: str
    description: str | None
    permissions: str | None
    created_at: datetime

class UserRoleAssignment(Base):
    __tablename__: str
    id: int
    user_id: int
    role_id: int
    assigned_at: datetime
    assigned_by: int | None

class UserPreferences(Base):
    __tablename__: str
    id: int
    user_id: int
    theme_mode: str
    language: str
    timezone: str
    currency: str

class UserSession(Base):
    __tablename__: str
    id: int
    user_id: int
    session_token: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime

class UserActivityLog(Base):
    __tablename__: str
    id: int
    user_id: int | None
    action: str
    resource: str | None
    details: str | None
    ip_address: str | None
    user_agent: str | None
    success: bool
    error_message: str | None
    created_at: datetime
