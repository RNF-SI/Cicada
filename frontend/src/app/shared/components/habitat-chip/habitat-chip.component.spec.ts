import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { of } from 'rxjs';
import { TranslateModule } from '@ngx-translate/core';

import { HabitatChipComponent } from './habitat-chip.component';
import { HabitatService } from '../../../core/services/habitat.service';

describe('HabitatChipComponent', () => {
  let component: HabitatChipComponent;
  let fixture: ComponentFixture<HabitatChipComponent>;
  let habitatService: { getCorrespondances: jest.Mock };

  const mockResponse = {
    habitat: { cd_hab: 1000, lb_code: 'G1.6', lb_typo: 'EUNIS', lb_hab_fr: 'Hêtraies', lb_hab_fr_complet: null, niveau: 3 },
    related: [
      { id: 1, cd_hab: 1000, cd_hab_entre: 20, cd_typo_entre: 22, lb_typo: 'CORINE_biotopes', lb_code_entre: '41.1', lb_hab_entre: 'Hêtraies (CB)', niveau_entre: 2, type_rel: 'equiv' },
      { id: 2, cd_hab: 1000, cd_hab_entre: 21, cd_typo_entre: 22, lb_typo: 'CORINE_biotopes', lb_code_entre: '41.11', lb_hab_entre: 'Hêtraies acidiphiles (CB)', niveau_entre: 3, type_rel: 'equiv' },
    ],
  };

  beforeEach(async () => {
    habitatService = { getCorrespondances: jest.fn().mockReturnValue(of(mockResponse)) };

    await TestBed.configureTestingModule({
      imports: [HabitatChipComponent, TranslateModule.forRoot()],
      providers: [{ provide: HabitatService, useValue: habitatService }],
    }).compileComponents();

    fixture = TestBed.createComponent(HabitatChipComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('cdHab', 1000);
    fixture.componentRef.setInput('label', 'Hêtraies');
    fixture.detectChanges();
  });

  it('groups linked habitats by referentiel and exposes the typo name (#468)', fakeAsync(() => {
    component.toggle();
    tick();

    const result = component.relatedGroups();
    expect(result.total).toBe(2);
    expect(result.groups.length).toBe(1);
    expect(result.groups[0].typo).toBe('CORINE biotopes'); // underscores nettoyés
    expect(result.groups[0].items.map(i => i.code)).toEqual(['41.1', '41.11']);
    expect(result.groups[0].items.every(i => i.typo === 'CORINE biotopes')).toBe(true);
  }));

  it('renders the referentiel name in the expanded panel (#468)', fakeAsync(() => {
    component.toggle();
    tick();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent || '';
    expect(text).toContain('CORINE biotopes');
    expect(text).toContain('41.1');
    expect(text).toContain('Hêtraies (CB)');
  }));

  it('separates linked habitats into distinct referentiel groups when they differ (#468)', fakeAsync(() => {
    habitatService.getCorrespondances.mockReturnValue(of({
      habitat: mockResponse.habitat,
      related: [
        { ...mockResponse.related[0], lb_typo: 'EUNIS', lb_code_entre: 'G1.6', lb_hab_entre: 'A' },
        { ...mockResponse.related[1], lb_typo: 'CORINE_biotopes', lb_code_entre: '41.1', lb_hab_entre: 'B' },
      ],
    }));

    component.toggle();
    tick();

    const groups = component.relatedGroups().groups;
    expect(groups.map(g => g.typo)).toEqual(['CORINE biotopes', 'EUNIS']); // triés
  }));
});
