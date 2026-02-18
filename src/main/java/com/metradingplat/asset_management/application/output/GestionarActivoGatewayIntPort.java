package com.metradingplat.asset_management.application.output;

import java.util.List;
import java.util.Optional;

import com.metradingplat.asset_management.domain.models.Activo;

public interface GestionarActivoGatewayIntPort {
    Activo guardar(Activo objActivo);

    List<Activo> obtenerPorIdEscaner(Long idEscaner);

    List<Activo> obtenerTodos();

    Activo obtenerPorId(Long idActivo);

    Boolean existePorId(Long idActivo);

    Optional<Activo> buscarPorSymbolYEscaner(String symbol, Long idEscaner);

    void eliminarPorIdEscaner(Long idEscaner);
}
