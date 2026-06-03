import MenuIcon from "@mui/icons-material/Menu";
import SpaIcon from "@mui/icons-material/Spa";
import {
  AppBar,
  Box,
  Button,
  Container,
  Drawer,
  IconButton,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const navItems = [
  { label: "Каталог", to: "/catalog" },
  { label: "Мои растения", to: "/plants" },
  { label: "Календарь", to: "/calendar" },
  { label: "Профиль", to: "/profile" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { isAuthenticated, signOut, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  const navigation = (
    <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} sx={{ p: { xs: 2, md: 0 } }}>
      {navItems.map((item) => (
        <Button
          key={item.to}
          component={RouterLink}
          to={item.to}
          color={location.pathname.startsWith(item.to) ? "secondary" : "inherit"}
          onClick={() => setDrawerOpen(false)}
        >
          {item.label}
        </Button>
      ))}
    </Stack>
  );

  return (
    <Box className="hero-pattern" sx={{ minHeight: "100vh" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar>
          <IconButton edge="start" sx={{ display: { md: "none" }, mr: 1 }} onClick={() => setDrawerOpen(true)}>
            <MenuIcon />
          </IconButton>
          <Stack
            component={RouterLink}
            to="/"
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{ color: "primary.main", mr: 3 }}
          >
            <SpaIcon />
            <Typography variant="h6">PlantCare</Typography>
          </Stack>
          <Box sx={{ display: { xs: "none", md: "block" }, flex: 1 }}>{navigation}</Box>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ ml: "auto" }}>
            {isAuthenticated && (
              <Typography variant="body2" sx={{ display: { xs: "none", sm: "block" } }}>
                {user?.username}
              </Typography>
            )}
            {isAuthenticated ? (
              <Button color="primary" variant="outlined" onClick={handleSignOut}>
                Выйти
              </Button>
            ) : (
              <Button component={RouterLink} to="/auth" color="primary" variant="contained">
                Войти
              </Button>
            )}
          </Stack>
        </Toolbar>
      </AppBar>
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <Box sx={{ width: 260 }}>{navigation}</Box>
      </Drawer>
      <Container maxWidth="lg" sx={{ py: { xs: 3, md: 5 } }}>
        {children}
      </Container>
    </Box>
  );
}
