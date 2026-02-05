package com.metradingplat.asset_management.application.input;

import java.util.List;

import com.metradingplat.asset_management.domain.models.Activo;

public interface GestionarActivoCUIntPort {
    Activo procesarCambioEstado(Activo objActivo);

    Activo procesarSenal(Activo objActivo);

    List<Activo> obtenerActivosPorEscaner(Long idEscaner);

    List<Activo> listar();

    Activo obtenerPorId(Long idActivo);
}
