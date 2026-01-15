import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NavigationTileComponent, TileColor } from './navigation-tile.component';

describe('NavigationTileComponent', () => {
  let component: NavigationTileComponent;
  let fixture: ComponentFixture<NavigationTileComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NavigationTileComponent, RouterTestingModule]
    }).compileComponents();

    fixture = TestBed.createComponent(NavigationTileComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  describe('initialization', () => {
    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should have empty title by default', () => {
      expect(component.title).toBe('');
    });

    it('should have fi-rr-folder as default icon', () => {
      expect(component.uicon).toBe('fi-rr-folder');
    });

    it('should have / as default link', () => {
      expect(component.link).toBe('/');
    });

    it('should have primary as default color', () => {
      expect(component.color).toBe('primary');
    });
  });

  describe('isCustomIcon', () => {
    it('should return true for custom icons', () => {
      component.uicon = 'custom:my-icon';
      expect(component.isCustomIcon()).toBe(true);
    });

    it('should return false for Flaticon icons', () => {
      component.uicon = 'fi-rr-document';
      expect(component.isCustomIcon()).toBe(false);
    });

    it('should return false for empty string', () => {
      component.uicon = '';
      expect(component.isCustomIcon()).toBe(false);
    });
  });

  describe('getCustomIconPath', () => {
    it('should return correct path for custom icon', () => {
      component.uicon = 'custom:auction';
      expect(component.getCustomIconPath()).toBe('assets/images/icons/auction.svg');
    });

    it('should strip custom: prefix correctly', () => {
      component.uicon = 'custom:my-special-icon';
      expect(component.getCustomIconPath()).toBe('assets/images/icons/my-special-icon.svg');
    });
  });

  describe('getFlatIconClass', () => {
    it('should return class with fi prefix', () => {
      component.uicon = 'fi-rr-document';
      expect(component.getFlatIconClass()).toBe('fi fi-rr-document');
    });

    it('should work with different icon names', () => {
      component.uicon = 'fi-rr-search';
      expect(component.getFlatIconClass()).toBe('fi fi-rr-search');
    });
  });

  describe('getBackgroundImagePath', () => {
    it('should return correct path for primary color', () => {
      component.color = 'primary';
      expect(component.getBackgroundImagePath()).toBe('assets/images/tile-backgrounds/bg-primary.png');
    });

    it('should return correct path for salmon color', () => {
      component.color = 'salmon';
      expect(component.getBackgroundImagePath()).toBe('assets/images/tile-backgrounds/bg-salmon.png');
    });

    it('should return correct path for terra-cotta color', () => {
      component.color = 'terra-cotta';
      expect(component.getBackgroundImagePath()).toBe('assets/images/tile-backgrounds/bg-terra-cotta.png');
    });

    it('should return correct path for yellow color', () => {
      component.color = 'yellow';
      expect(component.getBackgroundImagePath()).toBe('assets/images/tile-backgrounds/bg-yellow.png');
    });

    it('should return correct path for pale-green color', () => {
      component.color = 'pale-green';
      expect(component.getBackgroundImagePath()).toBe('assets/images/tile-backgrounds/bg-pale-green.png');
    });
  });

  describe('getCornerShapePath', () => {
    it('should return correct path for primary color', () => {
      component.color = 'primary';
      expect(component.getCornerShapePath()).toBe('assets/images/corner-shapes/corner-primary.png');
    });

    it('should return correct path for salmon color', () => {
      component.color = 'salmon';
      expect(component.getCornerShapePath()).toBe('assets/images/corner-shapes/corner-salmon.png');
    });

    it('should return correct path for terra-cotta color', () => {
      component.color = 'terra-cotta';
      expect(component.getCornerShapePath()).toBe('assets/images/corner-shapes/corner-terra-cotta.png');
    });
  });

  describe('input changes', () => {
    it('should accept title input', () => {
      component.title = 'My Plans';
      fixture.detectChanges();
      expect(component.title).toBe('My Plans');
    });

    it('should accept color input', () => {
      component.color = 'salmon';
      fixture.detectChanges();
      expect(component.color).toBe('salmon');
    });

    it('should accept link input', () => {
      component.link = '/plans';
      fixture.detectChanges();
      expect(component.link).toBe('/plans');
    });
  });
});
