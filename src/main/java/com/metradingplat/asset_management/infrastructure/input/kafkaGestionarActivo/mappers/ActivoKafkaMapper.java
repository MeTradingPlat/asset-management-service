package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.mappers;

import org.mapstruct.Mapper;
import org.mapstruct.ReportingPolicy;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.DTOPetition.ActivoEstadoDTOPeticion;

@Mapper(componentModel = "spring", unmappedTargetPolicy = ReportingPolicy.IGNORE)
public interface ActivoKafkaMapper {
    Activo deDTOADominio(ActivoEstadoDTOPeticion dto);
}
