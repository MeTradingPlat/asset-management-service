package com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.mappers;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.input.kafkaGestionarActivo.DTOPetition.ActivoEstadoDTOPeticion;
import javax.annotation.processing.Generated;
import org.springframework.stereotype.Component;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2026-02-04T22:45:32-0500",
    comments = "version: 1.5.5.Final, compiler: Eclipse JDT (IDE) 3.45.0.v20260128-0750, environment: Java 21.0.9 (Eclipse Adoptium)"
)
@Component
public class ActivoKafkaMapperImpl implements ActivoKafkaMapper {

    @Override
    public Activo deDTOADominio(ActivoEstadoDTOPeticion dto) {
        if ( dto == null ) {
            return null;
        }

        Activo activo = new Activo();

        activo.setEstado( dto.getEstado() );
        activo.setIdEscaner( dto.getIdEscaner() );
        activo.setMetadatos( dto.getMetadatos() );
        activo.setNombreEscaner( dto.getNombreEscaner() );
        activo.setSymbol( dto.getSymbol() );

        return activo;
    }
}
