import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useParams } from "react-router-dom";

import { apiRequest, unwrapResults } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatusMessage } from "../components/StatusMessage";
import type { CareLog, CareTask, Paginated, UserPlant, WeatherRecommendation } from "../types/api";
import { formatDate, locationLabel, taskLabel } from "../utils/format";

interface LogForm {
  task_type: string;
  notes: string;
}

interface TaskForm {
  task_type: string;
  due_date: string;
  notes: string;
}

export function PlantDetailsPage() {
  const { id } = useParams();
  const [plant, setPlant] = useState<UserPlant | null>(null);
  const [logs, setLogs] = useState<CareLog[]>([]);
  const [tasks, setTasks] = useState<CareTask[]>([]);
  const [recommendation, setRecommendation] = useState<WeatherRecommendation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const logForm = useForm<LogForm>({ defaultValues: { task_type: "water" } });
  const taskForm = useForm<TaskForm>({
    defaultValues: { task_type: "water", due_date: new Date().toISOString().slice(0, 10) },
  });

  const loadData = async () => {
    const [plantData, logData, taskData] = await Promise.all([
      apiRequest<UserPlant>(`/plants/${id}/`),
      apiRequest<Paginated<CareLog>>("/care-logs/"),
      apiRequest<Paginated<CareTask>>("/care-tasks/"),
    ]);
    setPlant(plantData);
    setLogs(unwrapResults(logData).filter((item) => item.plant === Number(id)));
    setTasks(unwrapResults(taskData).filter((item) => item.plant === Number(id)));
    try {
      const weather = await apiRequest<WeatherRecommendation>(`/weather/recommendation/?plant_id=${id}`);
      setRecommendation(weather);
    } catch {
      setRecommendation(null);
    }
  };

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить карточку"))
      .finally(() => setLoading(false));
  }, [id]);

  const submitLog = logForm.handleSubmit(async (values) => {
    setError("");
    setSuccess("");
    try {
      await apiRequest<CareLog>("/care-logs/", {
        method: "POST",
        body: JSON.stringify({ plant: Number(id), task_type: values.task_type, notes: values.notes }),
      });
      logForm.reset({ task_type: values.task_type, notes: "" });
      await loadData();
      setSuccess("Запись ухода сохранена.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить уход");
    }
  });

  const submitTask = taskForm.handleSubmit(async (values) => {
    setError("");
    setSuccess("");
    try {
      await apiRequest<CareTask>("/care-tasks/", {
        method: "POST",
        body: JSON.stringify({ plant: Number(id), ...values }),
      });
      taskForm.reset({ task_type: values.task_type, due_date: values.due_date, notes: "" });
      await loadData();
      setSuccess("Задача добавлена в календарь.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить задачу");
    }
  });

  if (loading) {
    return <CircularProgress />;
  }

  if (!plant) {
    return <Alert severity="error">Растение не найдено.</Alert>;
  }

  return (
    <Box>
      <PageHeader
        title={plant.nickname}
        subtitle={`${plant.species_detail.name}: карточка ухода, погодная рекомендация, история и будущие задачи.`}
      />
      <StatusMessage error={error} success={success} />
      <Box className="card-grid" sx={{ mb: 3 }}>
        <Card>
          <CardContent>
            <Stack spacing={1.5}>
              <Typography variant="h5">Профиль растения</Typography>
              <Chip label={locationLabel(plant.location_type)} color="secondary" sx={{ alignSelf: "flex-start" }} />
              <Typography>Следующий полив: {formatDate(plant.next_watering_due)}</Typography>
              <Typography>Последний полив: {formatDate(plant.last_watered_at)}</Typography>
              <Typography color="text.secondary">{plant.notes || "Заметки пока не добавлены."}</Typography>
            </Stack>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack spacing={1.5}>
              <Typography variant="h5">Погодная подсказка</Typography>
              {recommendation ? (
                <>
                  <Typography>{recommendation.message}</Typography>
                  <Typography color="text.secondary">Осадки сегодня: {recommendation.precipitation_mm} мм</Typography>
                  <Chip
                    color={recommendation.should_water_today ? "warning" : "success"}
                    label={recommendation.should_water_today ? "Полить сегодня" : "Можно подождать"}
                    sx={{ alignSelf: "flex-start" }}
                  />
                </>
              ) : (
                <Typography color="text.secondary">Погодный сервис временно недоступен, используется базовый график.</Typography>
              )}
            </Stack>
          </CardContent>
        </Card>
      </Box>

      <Box className="card-grid" sx={{ mb: 3 }}>
        <Card>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Записать уход
            </Typography>
            <Stack component="form" spacing={2} onSubmit={submitLog}>
              <TextField select label="Тип ухода" SelectProps={{ native: true }} {...logForm.register("task_type")}>
                <option value="water">Полив</option>
                <option value="fertilize">Удобрение</option>
                <option value="repot">Пересадка</option>
                <option value="prune">Обрезка</option>
              </TextField>
              <TextField label="Комментарий" multiline minRows={3} {...logForm.register("notes")} />
              <Button type="submit" variant="contained">
                Сохранить запись
              </Button>
            </Stack>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Добавить задачу
            </Typography>
            <Stack component="form" spacing={2} onSubmit={submitTask}>
              <TextField select label="Тип задачи" SelectProps={{ native: true }} {...taskForm.register("task_type")}>
                <option value="water">Полив</option>
                <option value="fertilize">Удобрение</option>
                <option value="repot">Пересадка</option>
                <option value="prune">Обрезка</option>
              </TextField>
              <TextField label="Дата" type="date" InputLabelProps={{ shrink: true }} {...taskForm.register("due_date")} />
              <TextField label="Заметки" multiline minRows={3} {...taskForm.register("notes")} />
              <Button type="submit" variant="contained">
                Добавить в календарь
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>

      <Box className="card-grid">
        <Card>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Ближайшие задачи
            </Typography>
            <Stack spacing={1}>
              {tasks.map((task) => (
                <Chip key={task.id} label={`${taskLabel(task.task_type)}: ${formatDate(task.due_date)} (${task.status})`} />
              ))}
              {tasks.length === 0 && <Typography color="text.secondary">Задач пока нет.</Typography>}
            </Stack>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Typography variant="h5" sx={{ mb: 2 }}>
              История ухода
            </Typography>
            <Stack spacing={1}>
              {logs.map((log) => (
                <Typography key={log.id} variant="body2">
                  {formatDate(log.performed_at)} — {taskLabel(log.task_type)} {log.notes && `· ${log.notes}`}
                </Typography>
              ))}
              {logs.length === 0 && <Typography color="text.secondary">История пока пуста.</Typography>}
            </Stack>
          </CardContent>
        </Card>
      </Box>
    </Box>
  );
}
