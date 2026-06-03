export type LightLevel = "low" | "medium" | "high";
export type LocationType = "indoor" | "balcony";
export type TaskType = "water" | "fertilize" | "repot" | "prune";
export type TaskStatus = "pending" | "done" | "skipped";

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export interface PlantSpecies {
  id: number;
  name: string;
  latin_name: string;
  description: string;
  light: LightLevel;
  humidity: number;
  watering_interval_days: number;
  pet_safe: boolean;
  image_url: string;
}

export interface UserPlant {
  id: number;
  species: number;
  species_detail: PlantSpecies;
  nickname: string;
  location_type: LocationType;
  planted_at: string | null;
  notes: string;
  watering_interval_override: number | null;
  last_watered_at: string | null;
  next_watering_due: string;
  created_at: string;
}

export interface CareTask {
  id: number;
  plant: number;
  plant_name: string;
  task_type: TaskType;
  due_date: string;
  status: TaskStatus;
  notes: string;
  created_at: string;
}

export interface CareLog {
  id: number;
  plant: number;
  plant_name: string;
  task_type: TaskType;
  performed_at: string;
  notes: string;
}

export interface PlantCollection {
  id: number;
  name: string;
  description: string;
  plants: UserPlant[];
  created_at: string;
}

export interface WeatherRecommendation {
  should_water_today: boolean;
  next_watering_date: string;
  precipitation_mm: number;
  precipitation_tomorrow_mm: number;
  temperature_c: number;
  humidity_percent: number;
  rain_expected: boolean;
  weather_summary: string;
  message: string;
}
