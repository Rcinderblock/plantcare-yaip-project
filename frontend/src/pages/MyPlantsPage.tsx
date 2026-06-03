import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
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
import { UserPlantCard } from "../components/UserPlantCard";
import type { Paginated, PlantSpecies, UserPlant } from "../types/api";

interface PlantForm {
  species: string;
  nickname: string;
  location_type: "indoor" | "balcony";
  planted_at: string;
  watering_interval_override: string;
  notes: string;
}

export function MyPlantsPage() {
  const [species, setSpecies] = useState<PlantSpecies[]>([]);
  const [plants, setPlants] = useState<UserPlant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const form = useForm<PlantForm>({ defaultValues: { location_type: "indoor" } });

  const loadData = async () => {
    const [speciesData, plantsData] = await Promise.all([
      apiRequest<Paginated<PlantSpecies>>("/species/"),
      apiRequest<Paginated<UserPlant>>("/plants/"),
    ]);
    setSpecies(unwrapResults(speciesData));
    setPlants(unwrapResults(plantsData));
  };

  useEffect(() => {
    loadData()
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить растения"))
      .finally(() => setLoading(false));
  }, []);

  const submit = form.handleSubmit(async (values) => {
    setError("");
    setSuccess("");
    try {
      await apiRequest<UserPlant>("/plants/", {
        method: "POST",
        body: JSON.stringify({
          species: Number(values.species),
          nickname: values.nickname,
          location_type: values.location_type,
          planted_at: values.planted_at || null,
          watering_interval_override: values.watering_interval_override
            ? Number(values.watering_interval_override)
            : null,
          notes: values.notes,
        }),
      });
      form.reset({ location_type: "indoor", species: values.species });
      await loadData();
      setSuccess("Растение добавлено в личный список.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось добавить растение");
    }
  });

  return (
    <Box>
      <PageHeader
        title="Мои растения"
        subtitle="Личный список растений с формой добавления, заметками и быстрым переходом в карточку ухода."
      />
      <StatusMessage error={error} success={success} />
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h5" sx={{ mb: 2 }}>
            Добавить растение
          </Typography>
          <Box component="form" className="form-grid" onSubmit={submit}>
            <TextField
              select
              label="Вид"
              InputLabelProps={{ shrink: true }}
              SelectProps={{ native: true }}
              {...form.register("species", { required: true })}
            >
              <option value="" disabled>
                Выберите вид
              </option>
              {species.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </TextField>
            <TextField label="Имя растения" {...form.register("nickname", { required: true })} />
            <TextField
              select
              label="Место"
              InputLabelProps={{ shrink: true }}
              SelectProps={{ native: true }}
              {...form.register("location_type")}
            >
              <option value="indoor">В помещении</option>
              <option value="balcony">На балконе</option>
            </TextField>
            <TextField label="Дата посадки" type="date" InputLabelProps={{ shrink: true }} {...form.register("planted_at")} />
            <TextField
              label="Интервал полива, дней"
              type="number"
              inputProps={{ min: 1 }}
              {...form.register("watering_interval_override")}
            />
            <TextField label="Заметки" multiline minRows={2} {...form.register("notes")} />
            <Button type="submit" variant="contained" disabled={form.formState.isSubmitting}>
              Добавить
            </Button>
          </Box>
        </CardContent>
      </Card>

      {loading && <CircularProgress />}
      {!loading && plants.length === 0 && <Alert severity="info">Пока нет растений. Добавьте первое из каталога.</Alert>}
      <Box className="card-grid">
        {plants.map((plant) => (
          <UserPlantCard key={plant.id} plant={plant} />
        ))}
      </Box>
    </Box>
  );
}
