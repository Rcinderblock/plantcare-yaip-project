import { Alert, Box, Button, Card, CardContent, CircularProgress, Stack, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { apiRequest, unwrapResults } from "../api/client";
import { PageHeader } from "../components/PageHeader";
import { SpeciesCard } from "../components/SpeciesCard";
import type { Paginated, PlantSpecies } from "../types/api";

export function CatalogPage() {
  const [species, setSpecies] = useState<PlantSpecies[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    apiRequest<Paginated<PlantSpecies>>("/species/")
      .then((data) => setSpecies(unwrapResults(data)))
      .catch((err) => setError(err instanceof Error ? err.message : "Каталог недоступен"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Box>
      <PageHeader
        title="Каталог растений"
        subtitle="Справочник видов с базовым интервалом полива, требованиями к свету и влажности. Это плиточное отображение рассчитано на большое количество элементов."
      />

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2}>
            <div>
              <Typography variant="h5">MVP для реального ухода</Typography>
              <Typography color="text.secondary">
                Добавьте растение из каталога в личную коллекцию, настройте график и сверяйте полив с погодой.
              </Typography>
            </div>
            <Button component={RouterLink} to="/plants" variant="contained">
              Добавить свое растение
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {loading && <CircularProgress />}
      {error && <Alert severity="error">{error}</Alert>}
      {!loading && !error && species.length === 0 && (
        <Alert severity="info">Каталог пуст. Запустите `python manage.py seed_demo` на backend.</Alert>
      )}
      <Box className="card-grid">
        {species.map((item) => (
          <SpeciesCard key={item.id} species={item} />
        ))}
      </Box>
    </Box>
  );
}
