import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { ChangeEvent, useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { apiRequest, unwrapResults } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { StatusMessage } from "../components/StatusMessage";
import { useAuth } from "../context/AuthContext";
import { useColorMode } from "../context/ColorModeContext";
import type { Paginated, PlantCollection, UserPlant } from "../types/api";

interface CollectionForm {
  name: string;
  description: string;
  plant_ids: string[];
}

export function ProfilePage() {
  const { user } = useAuth();
  const { mode, toggleMode } = useColorMode();
  const [plants, setPlants] = useState<UserPlant[]>([]);
  const [collections, setCollections] = useState<PlantCollection[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const form = useForm<CollectionForm>();

  const loadData = async () => {
    const [plantData, collectionData] = await Promise.all([
      apiRequest<Paginated<UserPlant>>("/plants/"),
      apiRequest<Paginated<PlantCollection>>("/collections/"),
    ]);
    setPlants(unwrapResults(plantData));
    setCollections(unwrapResults(collectionData));
  };

  useEffect(() => {
    loadData().catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить профиль"));
  }, []);

  const submitCollection = form.handleSubmit(async (values) => {
    setError("");
    setSuccess("");
    try {
      await apiRequest<PlantCollection>("/collections/", {
        method: "POST",
        body: JSON.stringify({
          name: values.name,
          description: values.description,
          plant_ids: (values.plant_ids ?? []).map(Number),
        }),
      });
      form.reset();
      await loadData();
      setSuccess("Коллекция создана.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать коллекцию");
    }
  });

  const submitImport = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setSuccess("");
    if (!file) {
      setError("Выберите CSV-файл.");
      return;
    }
    try {
      const data = new FormData();
      data.append("file", file);
      const result = await apiRequest<{ created_count: number; errors: { row: number; error: string }[] }>("/import/plants/", {
        method: "POST",
        body: data,
      });
      await loadData();
      setSuccess(`Импортировано растений: ${result.created_count}. Ошибок: ${result.errors.length}.`);
      setFile(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось импортировать CSV");
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    setFile(event.target.files?.[0] ?? null);
  };

  return (
    <Box>
      <PageHeader
        title="Профиль и настройки"
        subtitle="Здесь находятся переключение светлой/темной темы, массовый CSV-импорт и коллекции растений со связью многие-ко-многим."
      />
      <StatusMessage error={error} success={success} />
      <Box className="card-grid" sx={{ mb: 3 }}>
        <Card>
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="h5">Аккаунт</Typography>
              <Typography>Пользователь: {user?.username}</Typography>
              <Typography color="text.secondary">Email: {user?.email || "не указан"}</Typography>
              <FormControlLabel
                control={<Switch checked={mode === "dark"} onChange={toggleMode} />}
                label={mode === "dark" ? "Темная тема" : "Светлая тема"}
              />
            </Stack>
          </CardContent>
        </Card>
        <Card>
          <CardContent>
            <Stack component="form" spacing={2} onSubmit={submitImport}>
              <Typography variant="h5">CSV-импорт</Typography>
              <Typography color="text.secondary">
                Колонки: species_name,nickname,location_type,watering_interval_days,notes.
              </Typography>
              <Button component="label" variant="outlined">
                Выбрать CSV
                <input hidden type="file" accept=".csv,text/csv" onChange={handleFileChange} />
              </Button>
              {file && <Chip label={file.name} sx={{ alignSelf: "flex-start" }} />}
              <Button type="submit" variant="contained">
                Импортировать
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Новая коллекция
          </Typography>
          <Box component="form" className="form-grid" onSubmit={submitCollection}>
            <TextField label="Название" {...form.register("name", { required: true })} />
            <TextField label="Описание" {...form.register("description")} />
            <Box>
              <Typography variant="body2" sx={{ mb: 1 }}>
                Растения в коллекции
              </Typography>
              <select multiple size={Math.max(3, Math.min(6, plants.length))} {...form.register("plant_ids")}>
                {plants.map((plant) => (
                  <option key={plant.id} value={plant.id}>
                    {plant.nickname}
                  </option>
                ))}
              </select>
            </Box>
            <Button type="submit" variant="contained">
              Создать коллекцию
            </Button>
          </Box>
        </CardContent>
      </Card>

      <Box className="card-grid">
        {collections.map((collection) => (
          <Card key={collection.id}>
            <CardContent>
              <Stack spacing={1}>
                <Typography variant="h6">{collection.name}</Typography>
                <Typography color="text.secondary">{collection.description || "Без описания"}</Typography>
                <Stack direction="row" flexWrap="wrap" gap={1}>
                  {collection.plants.map((plant) => (
                    <Chip key={plant.id} label={plant.nickname} />
                  ))}
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Box>
    </Box>
  );
}
