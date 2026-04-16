import { OrderSide, OrderType, UserRole } from "@/shared/types/domain";

export const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: "管理员",
  TRADER: "交易员",
  RESEARCHER: "研究员",
};

export const ORDER_SIDE_OPTIONS: Array<{ label: string; value: OrderSide }> = [
  { label: "买入", value: "BUY" },
  { label: "卖出", value: "SELL" },
];

export const ORDER_TYPE_OPTIONS: Array<{ label: string; value: OrderType }> = [
  { label: "限价单", value: "LIMIT" },
  { label: "市价单", value: "MARKET" },
  { label: "止损单", value: "STOP" },
];
