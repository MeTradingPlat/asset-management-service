package com.metradingplat.asset_management.infrastructure.output.persistence.mappers;

import com.metradingplat.asset_management.domain.models.Activo;
import com.metradingplat.asset_management.infrastructure.output.persistence.entitys.ActivoEntity;
import java.util.ArrayList;
import java.util.List;
import javax.annotation.processing.Generated;
import org.springframework.stereotype.Component;

@Generated(
    value = "org.mapstruct.ap.MappingProcessor",
    date = "2026-02-04T22:45:32-0500",
    comments = "version: 1.5.5.Final, compiler: Eclipse JDT (IDE) 3.45.0.v20260128-0750, environment: Java 21.0.9 (Eclipse Adoptium)"
)
@Component
public class ActivoMapperPersistenciaImpl implements ActivoMapperPersistencia {

    @Override
    public Activo mappearDeEntityAActivo(ActivoEntity entity) {
        if ( entity == null ) {
            return null;
        }

        Activo activo = new Activo();

        activo.setEstado( entity.getEstado() );
        activo.setFechaActualizacion( entity.getFechaActualizacion() );
        activo.setFechaDeteccion( entity.getFechaDeteccion() );
        activo.setIdActivo( entity.getIdActivo() );
        activo.setIdEscaner( entity.getIdEscaner() );
        activo.setMetadatos( entity.getMetadatos() );
        activo.setNombreEscaner( entity.getNombreEscaner() );
        activo.setSymbol( entity.getSymbol() );

        return activo;
    }

    @Override
    public ActivoEntity mappearDeActivoAEntity(Activo activo) {
        if ( activo == null ) {
            return null;
        }

        ActivoEntity activoEntity = new ActivoEntity();

        activoEntity.setEstado( activo.getEstado() );
        activoEntity.setFechaActualizacion( activo.getFechaActualizacion() );
        activoEntity.setFechaDeteccion( activo.getFechaDeteccion() );
        activoEntity.setIdActivo( activo.getIdActivo() );
        activoEntity.setIdEscaner( activo.getIdEscaner() );
        activoEntity.setMetadatos( activo.getMetadatos() );
        activoEntity.setNombreEscaner( activo.getNombreEscaner() );
        activoEntity.setSymbol( activo.getSymbol() );

        return activoEntity;
    }

    @Override
    public List<Activo> mappearListaDeEntityAActivo(List<ActivoEntity> entities) {
        if ( entities == null ) {
            return null;
        }

        List<Activo> list = new ArrayList<Activo>( entities.size() );
        for ( ActivoEntity activoEntity : entities ) {
            list.add( mappearDeEntityAActivo( activoEntity ) );
        }

        return list;
    }
}
