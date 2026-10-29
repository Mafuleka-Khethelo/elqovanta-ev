const STATUS_LABELS: Record<string, string> = {
  available: "Reported available",
  occupied: "Reported occupied",
  offline: "Offline",
  paused: "Coordination closed",
  unknown: "Not reported",
};

const STATE_LABELS: Record<string, string> = {
  charging: "Charging reported",
  paused: "Charging paused",
  finished_plugged: "Finished, still plugged in",
  unplugged: "Unplugged",
  waiting: "Waiting",
  offered: "Offer open",
  accepted: "Offer accepted",
  left: "Left the list",
  expired: "Offer expired",
  cancelled: "Cancelled",
};

const EVENT_LABELS: Record<string, string> = {
  session_started: "Plugged in and started charging",
  charging_paused: "Charging paused",
  charging_resumed: "Charging resumed",
  charging_finished: "Charging finished, still plugged in",
  unplugged: "Unplugged",
  manager_close: "Closed by a station manager",
  still_charging: "Driver reported they are still charging",
};

export function statusLabel(status: string) {
  return STATUS_LABELS[status] ?? status;
}

export function stateLabel(state: string) {
  return STATE_LABELS[state] ?? state;
}

export function eventLabel(eventType: string) {
  return EVENT_LABELS[eventType] ?? eventType;
}

export function formatDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remain = seconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m ${remain}s`;
  if (minutes > 0) return `${minutes}m ${remain}s`;
  return `${remain}s`;
}

export function formatWhen(value: string | null | undefined) {
  if (!value) return "Not recorded";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function coordinateNote(flag: string) {
  if (flag === "ok") return "A representative historical coordinate is shown on the map.";
  if (flag === "inconsistent") return "Historical coordinates for this exact name disagree, so it stays in the list and is left off the map.";
  if (flag === "invalid") return "The recorded coordinates were not usable, so this charger is listed but not mapped.";
  return "No usable coordinates were recorded, so this charger is listed but not mapped.";
}

export function fieldError(fields: { field: string; message: string }[] | undefined, name: string) {
  return fields?.find((item) => item.field === name || item.field.endsWith(name))?.message;
}
