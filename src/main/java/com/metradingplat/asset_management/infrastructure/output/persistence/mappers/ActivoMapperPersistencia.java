package com.metradingplat.asset_management.infrastructure.output.persistence.mappers;

import java.util.List;

import org.mapstruct.Mapper;
import org.mapstruct.ReportingPolicy;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.output.persistence.entitys.ActivoEntity;

@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface ActivoMapperPersistencia {
    Activo mappearDeEntityAActivo(ActivoEntity entity);

    ActivoEntity mappearDeActivoAEntity(Activo activo);

    List<Activo> mappearListaDeEntityAActivo(List<ActivoEntity> entities);
}
