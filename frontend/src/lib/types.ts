export type Role = "driver" | "manager" | "researcher";

export type User = {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_demonstration: boolean;
};

export type PortType = { name: string; origin: string };

export type ChargerCard = {
  id: string;
  station_key: string;
  display_name: string;
  is_historical: boolean;
  latitude: number | null;
  longitude: number | null;
  coordinates_on_map: boolean;
  coordinate_flag: "ok" | "missing" | "invalid" | "inconsistent";
  app_status: string;
  status_updated_at: string | null;
  status_source: string | null;
  timezone: string;
  coordination_enabled: boolean;
  service_capacity: number | null;
  port_types: PortType[];
  is_favourite: boolean;
  straight_line_km: number | null;
  waiting_count: number;
  active_session_count: number;
  next_estimated_target_at?: string | null;
};

export type ChargerDetail = ChargerCard & {
  manager_names: string[];
  your_queue_state: string | null;
  your_queue_position: number | null;
  your_offer_expires_at: string | null;
  your_session_id: string | null;
  departure_reports: { expected_at: string; reported_at: string }[];
  server_time: string;
};

export type SessionEvent = {
  id: string;
  event_type: string;
  reason: string | null;
  created_at: string;
  actor_name: string | null;
};

export type Session = {
  id: string;
  charger_id: string;
  charger_name: string;
  station_key: string;
  state: string;
  port_type?: string | null;
  plugged_in_at: string;
  unplugged_at: string | null;
  is_demonstration: boolean;
  connected_seconds: number;
  charging_seconds: number;
  noncharging_seconds: number;
  intervals: { started_at: string; ended_at: string | null }[];
  events: SessionEvent[];
};

export type QueueView = {
  participation: string;
  port_type?: string | null;
  server_time: string;
  position: number | null;
  waiting_count: number | null;
  offer_expires_at: string | null;
  session_id: string | null;
  charger: { id: string; display_name: string; app_status: string } | null;
};

export type Vehicle = {
  id: string;
  nickname: string;
  model_name: string | null;
  port_preference: string | null;
  battery_capacity_kwh: number | null;
  max_ac_kw: number | null;
  max_dc_kw: number | null;
};

export type ChargePlan = {
  vehicle_id: string | null;
  vehicle_label: string;
  battery_capacity_kwh: number;
  current_percent: number;
  target_percent: number;
  charging_kind: "AC" | "DC";
  average_power_kw: number;
};

export type ChargeEstimate = ChargePlan & {
  id?: string;
  version?: number;
  is_active?: boolean;
  anchor_at: string;
  estimated_target_at: string;
  energy_needed_kwh: number;
  duration_seconds: number;
  effective_power_kw: number;
  assumption: string;
};

export type ConversationSummary = {
  id: string;
  charger_id: string;
  charger_name: string;
  other_name: string;
  unread: number;
  last_body: string | null;
  last_at: string;
};

export type ChatMessage = {
  id: string;
  sender_id: string;
  sender_name: string;
  body: string;
  created_at: string;
  mine: boolean;
};

export type Notice = {
  id: string;
  title: string;
  body: string;
  destination: string;
  read_at: string | null;
  created_at: string;
};

export type Prediction = {
  mode: string;
  station_key: string;
  port_type: string;
  arrival_local: string;
  timezone: string;
  model_name: string;
  artifact_sha256: string;
  warning_cutoff: number;
  noncharging_threshold_minutes: number;
  probability: number;
  warning: boolean;
  station_sessions_30d: number;
  station_long_rate_30d: number | null;
  history_window_start: string;
  history_window_end_exclusive: string;
  derived_features: { arrival_hour: number; arrival_day: string; arrival_month: number };
  hourly: { arrival_hour: number; probability: number; warning: boolean }[];
  computed_at: string;
  limitations: string;
};

export type DriverGuidance = {
  available: boolean;
  reason?: string;
  mode?: string;
  warning?: boolean;
  port_type?: string;
  port_types?: string[];
  arrival_local?: string;
  arrival_station?: string;
  station_timezone?: string;
  checked_at?: string;
  historical_arrival_local?: string;
  timezone?: string;
  title?: string;
  suggestion?: string;
  explanation?: string;
  action_label?: string;
  action_href?: string;
};

export type Insights = {
  source: string;
  time_basis: string;
  station_key: string | null;
  start_date: string | null;
  end_date: string | null;
  session_count: number;
  long_noncharging_count: number;
  long_noncharging_percent: number | null;
  median_connected_minutes: number | null;
  median_charging_minutes: number | null;
  median_noncharging_minutes: number | null;
  arrivals_by_hour: { hour: number; count: number }[];
  arrivals_by_weekday: { weekday: string; count: number }[];
  chargers: { station_key: string; session_count: number; long_noncharging_percent: number }[];
};

export type ModelCard = {
  ready: boolean;
  reason: string | null;
  model_name?: string;
  artifact_sha256?: string;
  warning_cutoff?: number;
  noncharging_threshold_minutes?: number;
  history_window_days?: number;
  timezone?: string;
  validation_year?: number;
  test_year?: number;
  feature_columns?: string[];
  classifier_params?: Record<string, string | number | null>;
  metrics_match_reference?: boolean;
  metrics_table?: { index: string[]; columns: string[]; values: (string | number | null)[][] };
  confusion_matrix?: number[][];
  package_versions?: Record<string, string>;
  limitations: string;
  plain_language?: string | null;
};
