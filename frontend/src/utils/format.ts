export function formatDate(value: string | null | undefined) {
  if (!value) {
    return "не указано";
  }
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  }).format(new Date(value));
}

export function taskLabel(value: string) {
  const labels: Record<string, string> = {
    water: "Полив",
    fertilize: "Удобрение",
    repot: "Пересадка",
    prune: "Обрезка",
  };
  return labels[value] ?? value;
}

export function locationLabel(value: string) {
  return value === "balcony" ? "Балкон" : "Комната";
}
