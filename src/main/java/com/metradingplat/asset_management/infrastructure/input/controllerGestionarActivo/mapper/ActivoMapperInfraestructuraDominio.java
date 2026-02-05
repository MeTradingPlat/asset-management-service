package com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.mapper;

import java.util.List;

import org.mapstruct.Mapper;
import org.mapstruct.ReportingPolicy;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.controllerGestionarActivo.DTOAnswer.ActivoDTORespuesta;

@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface ActivoMapperInfraestructuraDominio {
    ActivoDTORespuesta mappearDeActivoARespuesta(Activo activo);

    List<ActivoDTORespuesta> mappearListaDeActivoARespuesta(List<Activo> activos);
}
