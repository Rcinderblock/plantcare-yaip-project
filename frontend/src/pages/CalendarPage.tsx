import {
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

import { apiRequest, unwrapResults } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatusMessage } from "../components/StatusMessage";
import type { CareTask, Paginated, UserPlant } from "../types/api";
import { formatDate, taskLabel } from "../utils/format";

interface TaskForm {
  plant: string;
  task_type: string;
  due_date: string;
  notes: string;
}

export function CalendarPage() {
  const [tasks, setTasks] = useState<CareTask[]>([]);
  const [plants, setPlants] = useState<UserPlant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const form = useForm<TaskForm>({
    defaultValues: { task_type: "water", due_date: new Date().toISOString().slice(0, 10) },
  });

  const loadData = async () => {
    const [taskData, plantData] = await Promise.all([
      apiRequest<Paginated<CareTask>>("/care-tasks/"),
      apiRequest<Paginated<UserPlant>>("/plants/"),
    ]);
    setTasks(unwrapResults(taskData));
    setPlants(unwrapResults(plantData));
  };

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить календарь"))
      .finally(() => setLoading(false));
  }, []);

  const submit = form.handleSubmit(async (values) => {
    setError("");
    setSuccess("");
    try {
      await apiRequest<CareTask>("/care-tasks/", {
        method: "POST",
        body: JSON.stringify({ ...values, plant: Number(values.plant) }),
      });
      await loadData();
      setSuccess("Задача добавлена.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить задачу");
    }
  });

  const completeTask = async (task: CareTask) => {
    setError("");
    setSuccess("");
    try {
      await apiRequest(`/care-tasks/${task.id}/complete/`, { method: "POST" });
      await loadData();
      setSuccess("Задача отмечена выполненной.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось завершить задачу");
    }
  };

  return (
    <Box>
      <PageHeader
        title="Календарь ухода"
        subtitle="Планируйте полив, пересадку, удобрение и обрезку. Выполнение задачи автоматически попадает в историю ухода."
      />
      <StatusMessage error={error} success={success} />
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Новая задача
          </Typography>
          <Box component="form" className="form-grid" onSubmit={submit}>
            <TextField select label="Растение" SelectProps={{ native: true }} {...form.register("plant", { required: true })}>
              <option value="">Выберите растение</option>
              {plants.map((plant) => (
                <option key={plant.id} value={plant.id}>
                  {plant.nickname}
                </option>
              ))}
            </TextField>
            <TextField select label="Тип" SelectProps={{ native: true }} {...form.register("task_type")}>
              <option value="water">Полив</option>
              <option value="fertilize">Удобрение</option>
              <option value="repot">Пересадка</option>
              <option value="prune">Обрезка</option>
            </TextField>
            <TextField label="Дата" type="date" InputLabelProps={{ shrink: true }} {...form.register("due_date")} />
            <TextField label="Заметки" {...form.register("notes")} />
            <Button type="submit" variant="contained">
              Добавить задачу
            </Button>
          </Box>
        </CardContent>
      </Card>

      {loading && <CircularProgress />}
      <Stack spacing={2}>
        {tasks.map((task) => (
          <Card key={task.id}>
            <CardContent>
              <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2}>
                <div>
                  <Typography variant="h6">
                    {taskLabel(task.task_type)} · {task.plant_name}
                  </Typography>
                  <Typography color="text.secondary">Срок: {formatDate(task.due_date)}</Typography>
                  {task.notes && <Typography>{task.notes}</Typography>}
                </div>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Chip label={task.status === "done" ? "Выполнено" : "Ожидает"} color={task.status === "done" ? "success" : "warning"} />
                  {task.status !== "done" && (
                    <Button variant="contained" onClick={() => completeTask(task)}>
                      Выполнить
                    </Button>
                  )}
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ))}
        {!loading && tasks.length === 0 && (
          <Card>
            <CardContent>
              <Typography color="text.secondary">В календаре пока нет задач.</Typography>
            </CardContent>
          </Card>
        )}
      </Stack>
    </Box>
  );
}
