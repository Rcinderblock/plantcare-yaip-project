import WaterDropIcon from "@mui/icons-material/WaterDrop";
import { Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { UserPlant } from "../types/api";
import { formatDate, locationLabel } from "../utils/format";

export function UserPlantCard({ plant }: { plant: UserPlant }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Stack spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="start" gap={1}>
            <div>
              <Typography variant="h6">{plant.nickname}</Typography>
              <Typography variant="body2" color="text.secondary">
                {plant.species_detail.name}
              </Typography>
            </div>
            <Chip size="small" label={locationLabel(plant.location_type)} color="secondary" />
          </Stack>
          <Stack direction="row" spacing={1} alignItems="center">
            <WaterDropIcon color="primary" fontSize="small" />
            <Typography variant="body2">Следующий полив: {formatDate(plant.next_watering_due)}</Typography>
          </Stack>
          <Typography variant="body2" color="text.secondary">
            {plant.notes || "Заметок пока нет."}
          </Typography>
          <Button component={RouterLink} to={`/plants/${plant.id}`} variant="contained">
            Открыть карточку
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
